#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from collections import defaultdict
import hashlib
import json
from pathlib import Path

import datetime
import shutil
import time
import traceback
from typing import Any
from uuid import uuid4

from flask import Flask, make_response, render_template, request, send_file, jsonify, redirect

APIKEY = Path('apikey.txt').read_text(encoding='utf-8').strip()

app = Flask(__name__, instance_relative_config=True)

UPTIME_DB = Path('uptime.json')
if not UPTIME_DB.exists():
    UPTIME_DB.write_bytes(b'{}')

ID_DB = Path('ids.json')
if not ID_DB.exists():
    ID_DB.write_bytes(b'{}')

CRON_DB = Path('crons.json')
if not CRON_DB.exists():
    CRON_DB.write_bytes(b'[]')

JOB_DB = Path('jobs.json')
if not JOB_DB.exists():
    JOB_DB.write_bytes(b'[]')

JOBS_PATH = Path('jobs')

for x in Path('.').glob('*.temp'):
    x.unlink()
    del x


JOB_DEFAULTS = dict(
    wait=0,
    scrolltoJs='',
    scrolltox=0,
    scrolltoy=0,
    preRunJs='',
    waitJs=0,
    checkReadyJs='',
)


class TempFile:
    def __init__(self, place='/tmp') -> None:
        self.file = Path(f'{place}/{uuid4().hex}.temp')

    def __enter__(self) -> Path:
        self.file.touch()
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.file.exists():
            self.file.unlink()

    @classmethod
    def save_bytes(cls, dest: Path, b: bytes):
        with cls('.') as f:
            f.write_bytes(b)
            dest.parent.mkdir(parents=True, exist_ok=True)
            f.rename(dest)

    @classmethod
    def save_utf8(cls, dest: Path, s: str):
        with cls('.') as f:
            f.write_text(s, encoding='utf-8')
            dest.parent.mkdir(parents=True, exist_ok=True)
            f.rename(dest)


def next_id(name: str) -> int:
    ids = json.loads(ID_DB.read_text(encoding='utf-8'))
    if name not in ids:
        ids[name] = 0
    ids[name] += 1
    TempFile.save_utf8(ID_DB, json.dumps(ids))
    return ids[name]


@app.route('/', methods=['HEAD', 'OPTIONS', 'GET'])
def index():
    return 'Nothing to see here'


def get_updated_job_list() -> list[dict[str, Any]]:
    tm = time.time()
    crons: list[dict[str, Any]] = json.loads(
        CRON_DB.read_text(encoding='utf-8'))
    jobs: list[dict[str, Any]] = json.loads(JOB_DB.read_text(encoding='utf-8'))
    pendingCrons: list[dict[str, Any]] = (
        [*filter(lambda c: (tm-c['hours']*3600) > c['lastScheduledSec'], crons)])
    for pendingCron in pendingCrons:
        pendingCron['lastScheduledSec'] = tm
        jobs.append(dict(jobId=next_id('job'), **pendingCron))
    if len(pendingCrons):
        cronId2historySize: dict[int, int] = dict(
            map(lambda c: (c['cronId'], c['historySize']), crons))
        cronId2jobpos: dict[int, list[int]] = defaultdict(list)
        for i, job in enumerate(jobs):
            cronId2jobpos[job['cronId']].append(i)
        toDiscardPos: list[int] = list()
        for cronId, jobspos in cronId2jobpos.items():
            toDiscardPos += jobspos[:-round(cronId2historySize[cronId])]
        toDiscardPos.sort()
        toDiscardPos.reverse()
        for pos in toDiscardPos:
            job = jobs.pop(pos)
            job_path = JOBS_PATH.joinpath(f'{job["jobId"]:020d}')
            shutil.rmtree(job_path, ignore_errors=True)
        TempFile.save_utf8(CRON_DB, json.dumps(crons))
        TempFile.save_utf8(JOB_DB, json.dumps(jobs))
    return jobs


def worker_lastseen_update(name: str):
    namestrip = name.strip()
    if len(namestrip) > 0:
        uptimes: dict[str, float] = json.loads(
            UPTIME_DB.read_text(encoding='utf-8'))
        uptimes[namestrip] = time.time()
        TempFile.save_utf8(UPTIME_DB, json.dumps(uptimes))


def worker_get_next_job(worker: str) -> dict | None:
    for job in get_updated_job_list():
        if not JOBS_PATH.joinpath(f'{job["jobId"]:020d}/{worker}.zip').exists():
            return job
    return None


@app.route('/job/next', methods=['GET'])
def job_next_get():
    if APIKEY != request.args.get('key', '').strip():
        resp = make_response('wrong value for GET parameter: key')
        resp.status_code = 404
        return resp
    worker = request.args.get('worker', '')
    worker_lastseen_update(worker)
    next_job = worker_get_next_job(worker)
    if next_job is None:
        resp = make_response('no new job')
        resp.status_code = 404
        return resp
    return jsonify({**JOB_DEFAULTS, **next_job})


@app.route('/job', methods=['POST'])
def job_post():
    if APIKEY != request.args.get('key', '').strip():
        resp = make_response('wrong value for GET parameter: key')
        resp.status_code = 404
        return resp
    worker = request.args.get('worker', '')
    if worker.strip() == '':
        raise Exception('Unknown worker')
    worker_lastseen_update(worker)
    jobId = int(request.args.get('jobId', '0'))
    hashed = request.args.get('sha256', '')
    zfb = request.data
    m = hashlib.sha256()
    m.update(zfb)
    h = m.hexdigest()
    if h != hashed:
        raise ValueError('Sent data was not received right')
    TempFile.save_bytes(JOBS_PATH.joinpath(f'{jobId:020d}/{worker}.zip'), zfb)
    return jsonify('OK')


@app.route('/cron', methods=['GET'])
def cron():
    return send_file(CRON_DB)


@app.route('/cron/form', methods=['GET', 'POST'])
def cron_form():
    if request.method.upper() == 'GET':
        if request.args.get('apikey', '').strip() and APIKEY != request.args.get('apikey', '').strip():
            return redirect('/cron/form')
        return send_file(Path('cronform.html'))
    elif request.method.upper() == 'POST':
        if APIKEY != request.form.get('apikey', '').strip():
            return redirect('/cron/form')
        elif request.form['action'] == 'add':
            cronId = next_id('cron')
            cron = {
                **JOB_DEFAULTS,
                **dict(
                    cronId=cronId,
                    url=request.form['url'].strip(),
                    hours=float(request.form['hours'].strip()),
                    historySize=float(request.form['historySize'].strip()),
                    lastScheduledSec=time.time()-3600 *
                    float(request.form['hours'].strip()),
                    preRunJs=request.form['preRunJs'].strip(),
                    wait=float(request.form['wait'].strip()),
                    scrolltoJs=request.form['scrolltoJs'].strip(),
                    scrolltox=float(request.form['scrolltox'].strip()),
                    scrolltoy=float(request.form['scrolltoy'].strip()),
                    checkReadyJs=request.form['checkReadyJs'].strip(),
                    waitJs=float(request.form['waitJs'].strip()),
                )
            }
            crons = json.loads(CRON_DB.read_text(encoding='utf-8'))
            crons.append(cron)
            TempFile.save_utf8(CRON_DB, json.dumps(crons))
            return redirect('/cron/form?message=added%20successfully&apikey=' + request.form['apikey'])
        elif request.form['action'] == 'delete':
            cronId = int(request.form['cronId'].strip())
            crons = json.loads(CRON_DB.read_text(encoding='utf-8'))
            crons = [*filter(lambda c: c['cronId'] != cronId, crons)]
            TempFile.save_utf8(CRON_DB, json.dumps(crons))
            return redirect('/cron/form?message=deleted%20successfully&apikey=' + request.form['apikey'])
