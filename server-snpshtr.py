#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import hashlib
import json
from pathlib import Path

import datetime
import time
import traceback
from uuid import uuid4

from flask import Flask, make_response, render_template, request, send_file, jsonify

APIKEY = Path('apikey.txt').read_text(encoding='utf-8').strip()

app = Flask(__name__, instance_relative_config=True)

UPTIME_DB = Path('uptime.json')
if not UPTIME_DB.exists():
    UPTIME_DB.write_bytes(b'{}')

JOBS_PATH = Path('jobs')

for x in Path('.').glob('*.temp'):
    x.unlink()
    del x


class TempFile:
    def __init__(self, place='/tmp') -> None:
        self.file = Path(f'{place}/{uuid4().hex}.temp')

    def __enter__(self) -> Path:
        self.file.touch()
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.file.exists():
            self.file.unlink()


@app.route('/', methods=['HEAD', 'OPTIONS', 'GET'])
def index():
    return 'Nothing to see here'


def worker_lastseen_update(name: str):
    namestrip = name.strip()
    if len(namestrip) > 0:
        with TempFile('.') as f:
            uptimes: dict[str, float] = json.loads(
                UPTIME_DB.read_text(encoding='utf-8'))
            uptimes[namestrip] = time.time()
            f.write_text(json.dumps(uptimes))
            f.rename(UPTIME_DB)


@app.route('/job/next', methods=['GET'])
def job_next_get():
    if APIKEY != request.args.get('key', '').strip():
        resp = make_response('wrong value for GET parameter: key')
        resp.status_code = 404
        return resp
    worker_lastseen_update(request.args.get('worker', ''))
    return jsonify(dict(
        jobId=1,
        wait=0,
        scrolltox=0,
        scrolltoy=0,
        preRunJs='',
        waitJs=0,
        url='https://bff.furmeet.app',
    ))


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
    with TempFile('.') as f:
        f.write_bytes(zfb)
        dest = JOBS_PATH.joinpath(f'{jobId:020d}/{worker}.zip')
        dest.parent.mkdir(parents=True, exist_ok=True)
        f.rename(dest)
    return jsonify('OK')
