#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import hashlib
import importlib
from io import BytesIO
import json
from pathlib import Path
import socket
import subprocess
import sys
import traceback
import PIL.Image
import requests
import time
import zipfile
from playwright.sync_api import sync_playwright, Browser, Page


TEST_W, TEST_H = 800, 600

BASEAPI = Path('baseapi.txt').read_text(encoding='utf-8').strip()
APIKEY = Path('apikey.txt').read_text(encoding='utf-8').strip()
UPDURL = Path('updurl.txt').read_text(encoding='utf-8').strip()

HOSTNAME = socket.gethostname()
# PLATFORM = sys.platform
PLATFORM = 'docker'


def get_git_asset_url(fl: str) -> str:
    return UPDURL.rsplit('/', 1)[0]+'/'+fl


def get_content_checking(fl: str) -> bytes:
    resp = requests.get(fl)
    resp.raise_for_status()
    return resp.content


def get_git_asset(fl: str) -> bytes:
    return get_content_checking(get_git_asset_url(fl))


def run_hide_scrollbar(browser: Page):
    return browser.evaluate(
        '''
        (function(){
            const newStyle = document.createElement('style');
            newStyle.innerHTML = '::-webkit-scrollbar {display: none !important;} ' +
                '* {scrollbar-width: none !important; scrollbar-color: transparent !important;}';
            document.head.appendChild(newStyle);
        })();
        '''.strip()
    )


def run_job(browsers: list[tuple[str, Page]],
            resolutions_spec: list[tuple[str, tuple[int, int]]],
            jobId: int,
            hideScrollbar: bool,
            wait: float,
            scrolltoJs: str,
            scrolltox: int,
            scrolltoy: int,
            preRunJs: str,
            waitJs: float,
            checkReadyJs: str,
            url: str):
    bio = BytesIO()
    zf = zipfile.ZipFile(
        bio, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9)
    for browser_name, browser in browsers:
        browser.goto('about:blank')
        browser.set_viewport_size(dict(width=TEST_W, height=TEST_H))
        actual_w, actual_h = PIL.Image.open(
            BytesIO(browser.screenshot())).size
        compensation_w, compensation_h = TEST_W-actual_w, TEST_H-actual_h
        browser.goto(url)
        if hideScrollbar:
            run_hide_scrollbar(browser)
        browser.evaluate(preRunJs)
        time.sleep(waitJs)
        if checkReadyJs:
            while (waitReady := browser.evaluate(checkReadyJs)) > 0:
                time.sleep(waitReady)
        for resolution_name, (resw, resh) in resolutions_spec:
            browser.set_viewport_size(
                dict(width=resw+compensation_w, height=resh+compensation_h))
            if scrolltoJs:
                browser.evaluate(scrolltoJs)
            else:
                browser.evaluate(
                    f'window.scrollTo({scrolltox}, {scrolltoy})')
            if hideScrollbar:
                run_hide_scrollbar(browser)
            time.sleep(wait)
            # if hasattr(browser, 'get_full_page_screenshot_as_png'):
            #     zf.writestr(
            #         f'{PLATFORM}.{HOSTNAME}.{browser_name}.{resolution_name}.full.png',
            #         browser.screenshot()
            #     )
            scrsht = browser.screenshot()
            im = PIL.Image.open(BytesIO(scrsht))
            if im.size == (resw, resh):
                zf.writestr(
                    f'{PLATFORM}.{HOSTNAME}.{browser_name}.{resolution_name}.partial.png',
                    scrsht
                )
            del im
            del scrsht
        browser.goto('about:blank')
    zf.close()
    b = bio.getvalue()
    m = hashlib.sha256()
    m.update(b)
    h = m.hexdigest()
    requests.post(
        f'{BASEAPI}/job?key={APIKEY}&worker={HOSTNAME}&jobId={jobId}&sha256={h}',
        headers={'content-type': 'application/zip',
                 'content-length': str(len(b))},
        data=b).raise_for_status()
    # Path(f'{PLATFORM}.{jobId:012d}.zip').write_bytes(bio.getvalue())
    print(f'[INFO] Uploaded results for job {jobId} successfully')
    del zf
    del bio
    del b


def initialize_and_run_job(
    jobId: int,
    hideScrollbar: bool,
    wait: float,
    scrolltoJs: str,
    scrolltox: int,
    scrolltoy: int,
    preRunJs: str,
    waitJs: float,
    checkReadyJs: str,
    url: str,
):
    resolutions_spec = [
        (str(n), (int(v.split('x')[0]), int(v.split('x')[1])))
        for n, v in json.loads(Path('resolutions.json').read_text(
            encoding='utf-8'))['resolutions']]
    with sync_playwright() as p:
        browsers: list[tuple[str, Browser]] = [(browser_name, browser_type.launch()) for browser_name, browser_type in [
            ('chrome', p.chromium), ('firefox', p.firefox), ('webkit', p.webkit)]]
        tabs = [(name, browser.new_page()) for name, browser in browsers]
        run_job(
            tabs,
            resolutions_spec,
            jobId,
            hideScrollbar,
            wait,
            scrolltoJs,
            scrolltox,
            scrolltoy,
            preRunJs,
            waitJs,
            checkReadyJs,
            url,
        )


def self_update():
    global self_update, gather_next_job
    pss = Path(__file__)
    try:
        ncnt = get_git_asset(pss.name)
        if ncnt != pss.read_bytes():
            if not Path('.git').exists():
                pss.write_bytes(ncnt)
    except Exception:
        print('[WARN] Could not update')
        raise
    importlib.invalidate_caches()
    selfmodule = importlib.import_module(pss.stem)
    importlib.reload(selfmodule)
    gather_next_job = selfmodule.gather_next_job
    self_update = selfmodule.self_update


def subprocess_run_job(
    jobId: int,
    hideScrollbar: bool,
    wait: float,
    scrolltoJs: str,
    scrolltox: int,
    scrolltoy: int,
    preRunJs: str,
    waitJs: float,
    checkReadyJs: str,
    url: str
):
    return subprocess.run([
        sys.executable, sys.argv[0],
        str(jobId),
        str(int(hideScrollbar)),
        str(wait),
        str(scrolltoJs),
        str(scrolltox),
        str(scrolltoy),
        str(preRunJs),
        str(waitJs),
        str(checkReadyJs),
        str(url),
    ],
        text=True, check=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
        stdin=sys.stdin,
    )


def gather_next_job():
    try:
        resp = requests.get(
            f'{BASEAPI}/job/next?key={APIKEY}&worker={HOSTNAME}')
    except requests.exceptions.ConnectionError:
        time.sleep(10)
        return
    if resp.status_code == 404:
        print('[INFO] No new job')
        time.sleep(60)
    elif resp.status_code == 200:
        job = resp.json()
        print(f'[INFO] Running job {job["jobId"]}')
        subprocess_run_job(
            job['jobId'],
            bool(job['hideScrollbar']),
            job['wait'],
            job['scrolltoJs'],
            job['scrolltox'],
            job['scrolltoy'],
            job['preRunJs'],
            job['waitJs'],
            job['checkReadyJs'],
            job['url'],
        )
    else:
        try:
            resp.raise_for_status()
            raise ValueError(f'Unknown status code: {resp.status_code}')
        except Exception:
            print(traceback.format_exc())
        time.sleep(30)


def main():
    if len(sys.argv) == 1:
        while True:
            try:
                self_update()
                gather_next_job()
            except Exception:
                print(traceback.format_exc())
                time.sleep(2)
    elif len(sys.argv) == 11:
        [jobId_str,
         hideScrollbar_str,
         wait_str,
         scrolltoJs_str,
         scrolltox_str,
         scrolltoy_str,
         preRunJs_str,
         waitJs_str,
         checkReadyJs_str,
         url_str,] = sys.argv[1:]
        jobId = int(jobId_str)
        hideScrollbar = bool(int(hideScrollbar_str))
        wait = float(wait_str)
        scrolltoJs = str(scrolltoJs_str)
        scrolltox = int(float(scrolltox_str))
        scrolltoy = int(float(scrolltoy_str))
        preRunJs = str(preRunJs_str)
        waitJs = float(waitJs_str)
        checkReadyJs = str(checkReadyJs_str)
        url = str(url_str)
        initialize_and_run_job(
            jobId,
            hideScrollbar,
            wait,
            scrolltoJs,
            scrolltox,
            scrolltoy,
            preRunJs,
            waitJs,
            checkReadyJs,
            url,
        )
    else:
        raise ValueError(f'Wrong number of arguments: {len(sys.argv)}')


if __name__ == '__main__':
    main()
