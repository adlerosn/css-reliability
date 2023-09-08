#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import hashlib
import importlib
from io import BytesIO
import json
from pathlib import Path
import socket
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
            if hasattr(browser, 'get_full_page_screenshot_as_png'):
                zf.writestr(
                    f'{sys.platform}.{socket.gethostname()}.{browser_name}.{resolution_name}.full.png',
                    browser.screenshot()
                )
            zf.writestr(
                f'{sys.platform}.{socket.gethostname()}.{browser_name}.{resolution_name}.partial.png',
                browser.screenshot()
            )
        browser.goto('about:blank')
    zf.close()
    b = bio.getvalue()
    m = hashlib.sha256()
    m.update(b)
    h = m.hexdigest()
    requests.post(
        f'{BASEAPI}/job?key={APIKEY}&worker={socket.gethostname()}&jobId={jobId}&sha256={h}',
        headers={'content-type': 'application/zip',
                 'content-length': str(len(b))},
        data=b).raise_for_status()
    # Path(f'{sys.platform}.{jobId:012d}.zip').write_bytes(bio.getvalue())
    print(f'[INFO] Uploaded results for job {jobId} successfully')
    del zf
    del bio
    del b


def gather_next_job(browsers: list[tuple[str, Browser]], resolutions_spec: list[tuple[str, tuple[int, int]]]):
    try:
        resp = requests.get(
            f'{BASEAPI}/job/next?key={APIKEY}&worker={socket.gethostname()}')
    except requests.exceptions.ConnectionError:
        time.sleep(10)
        return
    if resp.status_code == 404:
        print('[INFO] No new job')
        time.sleep(60)
    elif resp.status_code == 200:
        job = resp.json()
        tabs = [(name, browser.new_page()) for name, browser in browsers]
        print(f'[INFO] Running job {job["jobId"]}')
        try:
            run_job(
                tabs,
                resolutions_spec,
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
        finally:
            for _, tab in tabs:
                tab.close()
        time.sleep(2)
    else:
        try:
            resp.raise_for_status()
            raise ValueError(f'Unknown status code: {resp.status_code}')
        except Exception:
            print(traceback.format_exc())
        time.sleep(30)


def self_update():
    global gather_next_job, run_job
    resp = requests.get(UPDURL.rsplit('/', 1)[0]+'/'+'client-dckshtr.py')
    resp.raise_for_status()
    if resp.content != Path('client-dckshtr.py').read_bytes():
        if not Path('.git').exists():
            Path('client-dckshtr.py').write_bytes(resp.content)
    importlib.invalidate_caches()
    selfmodule = importlib.import_module('client-dckshtr')
    importlib.reload(selfmodule)
    gather_next_job = selfmodule.gather_next_job
    run_job = selfmodule.run_job


def main():
    resolutions_spec = [
        (str(n), (int(v.split('x')[0]), int(v.split('x')[1])))
        for n, v in json.loads(Path('resolutions.json').read_text(
            encoding='utf-8'))['resolutions']]
    with sync_playwright() as p:
        browsers: list[tuple[str, Browser]] = [(browser_name, browser_type.launch()) for browser_name, browser_type in [
            ('chrome', p.chromium), ('firefox', p.firefox), ('webkit', p.webkit)]]
        while len(browsers):
            try:
                self_update()
                gather_next_job(browsers, resolutions_spec)
            except Exception:
                print(traceback.format_exc())
                time.sleep(5)


if __name__ == '__main__':
    main()
