#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from collections import defaultdict
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile
from flask_cors import CORS

import shutil
import time
from typing import Any
from uuid import uuid4

from flask import Flask, make_response, request, send_file, jsonify, redirect

APIKEY = Path('apikey.txt').read_text(encoding='utf-8').strip()

app = Flask(__name__, instance_relative_config=True)
CORS(app)

UPTIME_DB = Path('uptime.json')
if not UPTIME_DB.exists():
    UPTIME_DB.write_bytes(b'{}')

UPTIME2_DB = Path('uptime2.json')
if not UPTIME2_DB.exists():
    UPTIME2_DB.write_bytes(b'{}')

ID_DB = Path('ids.json')
if not ID_DB.exists():
    ID_DB.write_bytes(b'{}')

CRON_DB = Path('crons.json')
if not CRON_DB.exists():
    CRON_DB.write_bytes(b'[]')

JOB_DB = Path('jobs.json')
if not JOB_DB.exists():
    JOB_DB.write_bytes(b'[]')

ANAL_DB = Path('analysis.json')
if not ANAL_DB.exists():
    ANAL_DB.write_bytes(b'[]')

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
    anals: list[dict[str, Any]] = json.loads(
        ANAL_DB.read_text(encoding='utf-8'))
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
        #
        cronId2jobpos: dict[int, list[int]] = defaultdict(list)
        for i, job in enumerate(jobs):
            cronId2jobpos[job['cronId']].append(i)
        toDiscardPos: list[int] = list()
        for cronId, jobspos in cronId2jobpos.items():
            toDiscardPos += jobspos[:-round(cronId2historySize[cronId])]
        #
        for pos in toDiscardPos:
            anals = [*filter(
                lambda a: a["jobId"] != jobs[pos]["jobId"],
                anals)]
        #
        toDiscardPos.sort()
        toDiscardPos.reverse()
        for pos in toDiscardPos:
            job = jobs.pop(pos)
            job_path = JOBS_PATH.joinpath(f'{job["jobId"]:020d}')
            shutil.rmtree(job_path, ignore_errors=True)
        TempFile.save_utf8(ANAL_DB, json.dumps(anals))
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


def analizer_lastseen_update(name: str):
    namestrip = name.strip()
    if len(namestrip) > 0:
        uptimes: dict[str, float] = json.loads(
            UPTIME2_DB.read_text(encoding='utf-8'))
        uptimes[namestrip] = time.time()
        TempFile.save_utf8(UPTIME2_DB, json.dumps(uptimes))


def worker_get_next_job(worker: str) -> dict | None:
    for job in get_updated_job_list():
        if not JOBS_PATH.joinpath(f'{job["jobId"]:020d}/{worker}.zip').exists():
            return job
    return None


def get_updated_analysis_list() -> list[dict[str, Any]]:
    jobs = raw_job_submission_get()
    anals: list[dict[str, Any]] = json.loads(
        ANAL_DB.read_text(encoding='utf-8'))
    upd: bool = False
    for job in jobs:
        cronId = job['cronId']
        jobId = job['jobId']
        anal = next(filter(lambda a: a['jobId'] == jobId, anals), None)
        completeness = len([*filter(
            lambda f: f is not None,
            job['workers'].values()
        )])
        if anal is None or anal['completeness'] != completeness:
            upd = True
            anal2 = dict(
                cronId=cronId,
                jobId=jobId,
                finished=False,
                assignee=None,
                assigneeTime=.0,
                completeness=completeness,
                workers=job['workers'],
                analysisFile=None,
                analysis=None,
            )
            if anal is None:
                anals.append(anal2)
            else:
                anal.update(anal2)
    if upd:
        TempFile.save_utf8(ANAL_DB, json.dumps(anals))
    return anals


def analyzer_get_next_job(worker: str) -> dict | None:
    tm = time.time()
    anals = get_updated_analysis_list()
    for anal in anals:
        if not anal['finished'] and anal['completeness'] > 0:
            if anal['assignee'] == worker and anal['assigneeTime']+300 < tm:
                return anal
            elif not anal['assignee'] or anal['assigneeTime']+300 >= tm:
                anal['assignee'] = worker
                anal['assigneeTime'] = tm
                TempFile.save_utf8(ANAL_DB, json.dumps(anals))
                return anal
            else:
                # this
                #     unfinished job
                # is considered to be
                #     assigned and
                #     still running
                # so
                #     try next job
                pass
    # there is no analysis to be ran
    return None


@app.route('/job/next', methods=['HEAD', 'OPTIONS', 'GET'])
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
    next_job = worker_get_next_job(worker)
    jobId = int(request.args.get('jobId', '0'))
    if next_job['jobId'] != jobId:
        raise ValueError('Wrong job')
    hashed = request.args.get('sha256', '')
    zfb = request.data
    m = hashlib.sha256()
    m.update(zfb)
    h = m.hexdigest()
    if h != hashed:
        raise ValueError('Sent data was not received right')
    TempFile.save_bytes(JOBS_PATH.joinpath(f'{jobId:020d}/{worker}.zip'), zfb)
    return jsonify('OK')


@app.route('/job', methods=['HEAD', 'OPTIONS', 'GET'])
def job_get():
    return send_file(JOB_DB)


def raw_job_submission_get() -> list[dict[str, Any]]:
    jobs = json.loads(JOB_DB.read_text(encoding='utf-8'))
    uptimes = json.loads(UPTIME_DB.read_text(encoding='utf-8'))
    for job in jobs:
        job['workers'] = dict()
        for worker in uptimes:
            workerzip = JOBS_PATH.joinpath(f'{job["jobId"]:020d}/{worker}.zip')
            job['workers'][worker] = None if not workerzip.exists() else str(workerzip)
    return jobs


@app.route('/job/submission', methods=['HEAD', 'OPTIONS', 'GET'])
def job_submission_get():
    return jsonify(raw_job_submission_get())


@app.route('/analysis', methods=['HEAD', 'OPTIONS', 'GET'])
def analysis_get():
    return send_file(ANAL_DB)


@app.route('/analysis/next', methods=['HEAD', 'OPTIONS', 'GET'])
def analysis_next_get():
    if APIKEY != request.args.get('key', '').strip():
        resp = make_response('wrong value for GET parameter: key')
        resp.status_code = 404
        return resp
    worker = request.args.get('worker', '')
    if worker.strip() == '':
        raise Exception('Unknown worker')
    analizer_lastseen_update(worker)
    next_job = analyzer_get_next_job(worker)
    if next_job is None:
        resp = make_response('no new job')
        resp.status_code = 404
        return resp
    return jsonify({**JOB_DEFAULTS, **next_job})


@app.route('/analysis', methods=['POST'])
def analysis_post():
    if APIKEY != request.args.get('key', '').strip():
        resp = make_response('wrong value for GET parameter: key')
        resp.status_code = 404
        return resp
    worker = request.args.get('worker', '')
    if worker.strip() == '':
        raise Exception('Unknown worker')
    analizer_lastseen_update(worker)
    next_anal = analyzer_get_next_job(worker)
    jobId = int(request.args.get('jobId', '0'))
    completeness = int(request.args.get('completeness', '0'))
    if next_anal['worker'] != worker:
        raise ValueError('Wrong job')
    if next_anal['jobId'] != jobId:
        raise ValueError('Wrong job')
    if next_anal['completeness'] != completeness:
        raise ValueError('Wrong job')
    hashed = request.args.get('sha256', '')
    zfb = request.data
    m = hashlib.sha256()
    m.update(zfb)
    h = m.hexdigest()
    if h != hashed:
        raise ValueError('Sent data was not received right')
    analysisFile = JOBS_PATH.joinpath(f'{jobId:020d}/analysis.zip')
    TempFile.save_bytes(analysisFile, zfb)
    zf = zipfile.ZipFile(BytesIO(zfb))
    anals: list[dict[str, Any]] = json.loads(
        ANAL_DB.read_text(encoding='utf-8'))
    for anal in anals:
        if anal['jobId'] == next_anal['jobId']:
            anal['finished'] = True
            anal['analysisFile'] = str(analysisFile)
            anal['analysis'] = json.loads(
                zf.read('analysis.json').decode(encoding='utf-8'))
            break
    TempFile.save_utf8(ANAL_DB, json.dumps(anals))
    return jsonify('OK')


@app.route('/uptime', methods=['HEAD', 'OPTIONS', 'GET'])
def uptime_get():
    return send_file(UPTIME_DB)


@app.route('/uptime2', methods=['HEAD', 'OPTIONS', 'GET'])
def uptime2_get():
    return send_file(UPTIME2_DB)


@app.route('/cron', methods=['HEAD', 'OPTIONS', 'GET'])
def cron():
    return send_file(CRON_DB)


@app.route('/cron/form', methods=['HEAD', 'OPTIONS', 'GET'])
def cron_form_get():
    if request.args.get('apikey', '').strip() and APIKEY != request.args.get('apikey', '').strip():
        return redirect('/cron/form')
    return send_file(Path('cronform.html'))


@app.route('/cron/form', methods=['POST'])
def cron_form_post():
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
