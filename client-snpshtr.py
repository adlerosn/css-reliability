#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import hashlib
import importlib
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import sys
import traceback
from typing import Union
import PIL.Image
import requests
from selenium import webdriver
import time
import zipfile


TEST_W, TEST_H = 800, 600

WDTP = Union[webdriver.Firefox, webdriver.Chrome,
             webdriver.Edge, webdriver.Safari]

CLS_OPTIONS = dict(
    Firefox=webdriver.FirefoxOptions,
    Chrome=webdriver.ChromeOptions,
    Edge=webdriver.EdgeOptions,
    Safari=getattr(webdriver, 'SafariOptions', webdriver.ChromeOptions),
)
CLS_WEBDRIVER = dict(
    Firefox=webdriver.Firefox,
    Chrome=webdriver.Chrome,
    Edge=webdriver.Edge,
    Safari=getattr(webdriver, 'Safari', webdriver.Chrome),
)

BASEAPI = Path('baseapi.txt').read_text(encoding='utf-8').strip()
APIKEY = Path('apikey.txt').read_text(encoding='utf-8').strip()
UPDURL = Path('updurl.txt').read_text(encoding='utf-8').strip()


def run_hide_scrollbar(browser: WDTP):
    return browser.execute_script(
        '''
        (function(){
            const newStyle = document.createElement('style');
            newStyle.innerHTML = '::-webkit-scrollbar {display: none !important;} ' +
                '* {scrollbar-width: none !important; scrollbar-color: transparent !important;}';
            document.head.appendChild(newStyle);
        })();
        '''.strip()
    )


def run_job(browsers: list[WDTP],
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
    for browser in browsers:
        browser.get('about:blank')
        browser.set_window_size(TEST_W, TEST_H)
        actual_w, actual_h = PIL.Image.open(
            BytesIO(browser.get_screenshot_as_png())).size
        compensation_w, compensation_h = TEST_W-actual_w, TEST_H-actual_h
        browser.get(url)
        if hideScrollbar:
            run_hide_scrollbar(browser)
        browser.execute_script(preRunJs)
        time.sleep(waitJs)
        if checkReadyJs:
            while (waitReady := browser.execute_script(checkReadyJs)) > 0:
                time.sleep(waitReady)
        for resolution_name, (resw, resh) in resolutions_spec:
            browser.set_window_size(resw+compensation_w, resh+compensation_h)
            if scrolltoJs:
                browser.execute_script(scrolltoJs)
            else:
                browser.execute_script(
                    f'window.scrollTo({scrolltox}, {scrolltoy})')
            if hideScrollbar:
                run_hide_scrollbar(browser)
            time.sleep(wait)
            if hasattr(browser, 'get_full_page_screenshot_as_png'):
                zf.writestr(
                    f'{sys.platform}.{socket.gethostname()}.{browser.name}.{resolution_name}.full.png',
                    browser.get_full_page_screenshot_as_png()
                )
            zf.writestr(
                f'{sys.platform}.{socket.gethostname()}.{browser.name}.{resolution_name}.partial.png',
                browser.get_screenshot_as_png()
            )
        browser.get('about:blank')
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


def gather_next_job(browsers: list[WDTP], resolutions_spec: list[tuple[str, tuple[int, int]]]):
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
        print(f'[INFO] Running job {job["jobId"]}')
        run_job(
            browsers,
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
    resp = requests.get(UPDURL)
    resp.raise_for_status()
    if resp.content != Path('client-snpshtr.py').read_bytes():
        if not Path('.git').exists():
            Path('client-snpshtr.py').write_bytes(resp.content)
    importlib.invalidate_caches()
    selfmodule = importlib.import_module('client-snpshtr')
    importlib.reload(selfmodule)
    gather_next_job = selfmodule.gather_next_job
    run_job = selfmodule.run_job


def main():
    browsers_spec = json.loads(Path(f'browsers.{sys.platform}.json').read_text(
        encoding='utf-8'))['browsers']
    resolutions_spec = [
        (str(n), (int(v.split('x')[0]), int(v.split('x')[1])))
        for n, v in json.loads(Path('resolutions.json').read_text(
            encoding='utf-8'))['resolutions']]
    browsers: WDTP = list()
    try:
        for browser_spec in browsers_spec:
            opt = CLS_OPTIONS[browser_spec['type']]()
            if os.environ.get('SKIP_ARGS', '') == '':
                for arg in browser_spec['arguments']:
                    opt.add_argument(arg)
            else:
                opt.headless = False
            try:
                browser = CLS_WEBDRIVER[browser_spec['type']](opt)
                browsers.append(browser)
            except Exception:
                print(
                    f'[ERROR] Could not initialize browser {browser_spec["type"]}')
                print(traceback.format_exc())
        for browser in browsers:
            browser.get('about:blank')
        while len(browsers):
            try:
                self_update()
                gather_next_job(browsers, resolutions_spec)
            except Exception:
                print(traceback.format_exc())
                time.sleep(5)
    finally:
        for browser in browsers:
            browser.close()


if __name__ == '__main__':
    main()
