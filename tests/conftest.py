import subprocess
import time
import os

import pytest

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), '..', 'infra', 'docker-compose.yml')
ENV_FILE = os.path.join(os.path.dirname(__file__), '..', 'infra', '.env.example')

@pytest.fixture(scope='session', autouse=True)
def stack():
    subprocess.run(['docker', 'compose', '-f', COMPOSE_FILE, '--env-file', ENV_FILE, 'up', '-d'], check=True)
    time.sleep(5)
    yield
    subprocess.run(['docker', 'compose', '-f', COMPOSE_FILE, 'down', '-v'], check=True)
