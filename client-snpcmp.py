#!/usr/bin/env python3


from concurrent.futures import Future, ProcessPoolExecutor
import hashlib
import json
import pandas
import importlib
import socket
import time
import traceback
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Iterable, Literal, TypeVar

import numpy
import PIL.Image
import requests

BASEAPI = Path('baseapi.txt').read_text(encoding='utf-8').strip()
APIKEY = Path('apikey.txt').read_text(encoding='utf-8').strip()
UPDURL = Path('updurl.txt').read_text(encoding='utf-8').strip()


_VT = TypeVar('_VT')


@dataclass
class BrowsingContext:
    platform: str
    hostname: str
    browser: str


@dataclass
class DisplayContext(BrowsingContext):
    screen: str


def flatten(lli: Iterable[Iterable[_VT]]) -> Iterable[_VT]:
    return (i for li in lli for i in li)


def get_git_asset_url(fl: str) -> str:
    return UPDURL.rsplit('/', 1)[0]+fl


def get_content_checking(fl: str) -> bytes:
    resp = requests.get(fl)
    resp.raise_for_status()
    return resp.content


def get_git_asset(fl: str) -> bytes:
    return get_content_checking(get_git_asset_url(fl))


def zip_in_memory_extract_all(zf: zipfile.ZipFile) -> dict[str, bytes]:
    return dict((zil.filename, zf.read(zil)) for zil in zf.infolist())


def into_rgb(pi: PIL.Image.Image) -> PIL.Image.Image:
    im = PIL.Image.new('RGB', pi.size, '#FFFFFF')
    im.paste(pi)
    return im


def into_rgb_max_size(pi: PIL.Image.Image, other_size: tuple[int, int]) -> PIL.Image.Image:
    im = PIL.Image.new('RGB', (
        max(pi.size[0], other_size[0]),
        max(pi.size[1], other_size[1])
    ), '#FFFFFF')
    im.paste(pi)
    return im


def dual_rgb_to_diff(rgb1: PIL.Image.Image, rgb2: PIL.Image.Image) -> PIL.Image.Image:
    np_1 = numpy.asarray(into_rgb_max_size(
        rgb1, rgb2.size)).astype(numpy.float64)
    np_2 = numpy.asarray(into_rgb_max_size(
        rgb2, rgb1.size)).astype(numpy.float64)
    e = np_1 - np_2
    eabs = e.__abs__().astype(numpy.uint8)
    return PIL.Image.fromarray(eabs)


def diff_to_rmse(i: PIL.Image.Image) -> float:
    e = numpy.asarray(i).astype(numpy.float64)
    se = e*e
    mse = se.sum()/se.size
    rmse = mse**.5
    return rmse


def img_to_png(i: PIL.Image.Image) -> bytes:
    bio = BytesIO()
    i.save(bio, format='PNG', optimize=True)
    return bio.getvalue()


def avg(li: list[int | float], on_empty: float | None = None) -> float:
    if len(li) <= 0:
        if on_empty is None:
            raise ValueError('List is empty')
        return on_empty
    return sum(li)/len(li)


def run_job(
    jobId: int,
    completeness: int,
    workers: dict[str, str | None],
):
    with ProcessPoolExecutor(16) as pe:
        name_images = {
            name: into_rgb(PIL.Image.open(BytesIO(bts)))
            for name, bts in
            [*flatten([
                zip_in_memory_extract_all(zipfile.ZipFile(
                    BytesIO(get_content_checking(f'{BASEAPI}/{worker}')))).items()
                for worker in workers.values() if worker is not None])]}
        samples: dict[str, list[tuple[BrowsingContext,
                                      PIL.Image.Image]]] = defaultdict(list)
        for name, im in name_images.items():
            plat, host, browser, sizing = name.split('.', 3)
            sizing = sizing.rsplit('.', 1)[0]
            bc = BrowsingContext(plat, host, browser)
            samples[sizing].append((bc, im))
            del plat, host, browser, name, im, bc
        del name_images
        sample_pairs_futdiff: dict[str,
                                   list[tuple[BrowsingContext,
                                              BrowsingContext,
                                              Future[PIL.Image.Image]]]] = defaultdict(list)
        for sizing, data_points in samples.items():
            if len(data_points) < 2:
                sample_pairs_futdiff[sizing] = list()
                continue
            for i, (bc1, im1) in enumerate(data_points[:-1]):
                for bc2, im2 in data_points[i+1:]:
                    pe.submit(dual_rgb_to_diff, im1, im2)
                    sample_pairs_futdiff[sizing].append(
                        (bc1, bc2, pe.submit(dual_rgb_to_diff, im1, im2)))
        del samples
        sample_pairs_diff: dict[str,
                                list[tuple[BrowsingContext,
                                           BrowsingContext,
                                           PIL.Image.Image]]] = {
            k: [(bc1, bc2, fut.result()) for bc1, bc2, fut in vs]
            for k, vs in sample_pairs_futdiff.items()
        }
        del sample_pairs_futdiff
        sample_pairs_futrmse: dict[str,
                                   list[tuple[BrowsingContext,
                                              BrowsingContext,
                                              Future[float]]]] = {
            k: [(bc1, bc2, pe.submit(diff_to_rmse, dif))
                for bc1, bc2, dif in vs]
            for k, vs in sample_pairs_diff.items()
        }
        sample_pairs_futbytes: dict[str,
                                    list[tuple[BrowsingContext,
                                               BrowsingContext,
                                               Future[bytes]]]] = {
            k: [(bc1, bc2, pe.submit(img_to_png, dif))
                for bc1, bc2, dif in vs]
            for k, vs in sample_pairs_diff.items()
        }
        del sample_pairs_diff
        sample_pairs_rmse: dict[str,
                                list[tuple[BrowsingContext,
                                           BrowsingContext,
                                           float]]] = {
            k: [(bc1, bc2, fut.result()) for bc1, bc2, fut in vs]
            for k, vs in sample_pairs_futrmse.items()
        }
        sample_pairs_bytes: dict[str,
                                 list[tuple[BrowsingContext,
                                            BrowsingContext,
                                            bytes]]] = {
            k: [(bc1, bc2, fut.result()) for bc1, bc2, fut in vs]
            for k, vs in sample_pairs_futbytes.items()
        }
        bzf = BytesIO()
        zf = zipfile.ZipFile(bzf, mode='w', compresslevel=9,
                             compression=zipfile.ZIP_DEFLATED)
        for fname, imcontents in flatten([
            [(
                (
                    '{}.{}.{}.{}.{}.{}.{}.{}.png'.format(
                        k.split('.')[0],
                        k.split('.')[1],
                        v1.hostname,
                        v2.hostname,
                        v1.platform,
                        v2.platform,
                        v1.browser,
                        v2.browser,
                    )
                ),
                v3,
            ) for v1, v2, v3 in vs]
            for k, vs in sample_pairs_bytes.items()
        ]):
            zf.writestr(fname, imcontents)
            del fname, imcontents
        df = pandas.DataFrame([
            *flatten([
                [(
                    k.split('.')[0],
                    k.split('.')[1],
                    v1.hostname,
                    v2.hostname,
                    v1.platform,
                    v2.platform,
                    v1.browser,
                    v2.browser,
                    v3,
                )
                    for v1, v2, v3 in vs]
                for k, vs in sample_pairs_rmse.items()])],
            columns=[
            'resolution',
            'printScope',
            'hostname1',
            'hostname2',
            'platform1',
            'platform2',
            'browser1',
            'browser2',
            'rmse',
        ]).sort_values(by=[
            'rmse',
            'resolution',
            'printScope',
            'hostname1',
            'hostname2',
            'platform1',
            'platform2',
            'browser1',
            'browser2',
        ])
        recordsio = StringIO()
        df.to_json(recordsio, orient='records')
        records = json.loads(recordsio.getvalue())
        major_difference:  dict[Literal['resolution'] | Literal['platform'] | Literal['browser'] | Literal['platformBrowser'], dict[str, list[float]]] = dict(
            resolution=defaultdict(list),
            platform=defaultdict(list),
            browser=defaultdict(list),
            platformBrowser=defaultdict(list),
        )
        for record in records:
            major_difference['resolution'][f"{record['resolution']}.{record['printScope']}"].append(
                record['rmse'])
            if record['platform1'] != record['platform2']:
                major_difference['platform'][record['platform1']].append(
                    record['rmse'])
                major_difference['platform'][record['platform2']].append(
                    record['rmse'])
            if record['browser1'] != record['browser2']:
                major_difference['browser'][record['browser1']].append(
                    record['rmse'])
                major_difference['browser'][record['browser2']].append(
                    record['rmse'])
            if record['platform1'] != record['platform2'] or record['browser1'] != record['browser2']:
                major_difference['platformBrowser'][f"{record['platform1']}.{record['browser1']}"].append(
                    record['rmse'])
                major_difference['platformBrowser'][f"{record['platform2']}.{record['browser2']}"].append(
                    record['rmse'])
        major_difference_avg = {
            k: {k2: avg(v) for k2, v in d2.items()} for k, d2 in major_difference.items()}
        report = dict(
            indicators=major_difference_avg,
            records=records,
        )
        zf.writestr('analysis.json', json.dumps(
            report, indent=4).encode(encoding='utf-8'))
        zf.close()
        b = bzf.getvalue()
        m = hashlib.sha256()
        m.update(b)
        h = m.hexdigest()
        requests.post(
            f'{BASEAPI}/analysis?key={APIKEY}&worker={socket.gethostname()}&jobId={jobId}&completeness={completeness}&sha256={h}',
            headers={'content-type': 'application/zip',
                     'content-length': str(len(b))},
            data=b).raise_for_status()
        print(f'[INFO] Uploaded analysis for job {jobId} successfully')


def gather_next_job():
    try:
        resp = requests.get(
            f'{BASEAPI}/analysis/next?key={APIKEY}&worker={socket.gethostname()}')
    except requests.exceptions.ConnectionError:
        time.sleep(10)
        return
    if resp.status_code == 404:
        print('[INFO] No new analysis')
        time.sleep(60)
    elif resp.status_code == 200:
        job = resp.json()
        print(f'[INFO] Running analysis {job["jobId"]}')
        run_job(
            job['jobId'],
            job['completeness'],
            job['workers'],
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
    try:
        newscript = get_git_asset('client-snpcmp.py')
        if newscript != Path('client-snpcmp.py').read_bytes():
            if not Path('.git').exists():
                Path('client-snpcmp.py').write_bytes(newscript)
    except Exception:
        pass
    importlib.invalidate_caches()
    selfmodule = importlib.import_module('client-snpcmp')
    importlib.reload(selfmodule)
    gather_next_job = selfmodule.gather_next_job
    run_job = selfmodule.run_job


def main():
    while True:
        try:
            self_update()
            gather_next_job()
        except Exception:
            print(traceback.format_exc())
            time.sleep(5)


if __name__ == '__main__':
    main()
