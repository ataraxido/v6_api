# [camptocamp.org](https://www.camptocamp.org) API

[![GitHub license](https://img.shields.io/github/license/c2corg/v6_api.svg)](https://github.com/c2corg/v6_api/blob/master/LICENSE) [![Build Status](https://travis-ci.org/c2corg/v6_api.svg?branch=master)](https://travis-ci.com/c2corg/v6_api) [![Total alerts](https://img.shields.io/lgtm/alerts/g/c2corg/v6_api.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/c2corg/v6_api/alerts/) [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/c2corg/v6_api.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/c2corg/v6_api/context:javascript) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/56217935d9cd43458eb5539ce52a8628)](https://app.codacy.com/app/c2corg/v6_api?utm_source=github.com&utm_medium=referral&utm_content=c2corg/v6_api&utm_campaign=Badge_Grade_Dashboard) [![Known Vulnerabilities](https://snyk.io/test/github/c2corg/v6_api/badge.svg)](https://snyk.io/test/github/c2corg/v6_api)

## Development environment
On any OS, install [git](https://git-scm.com/) and [docker](https://docs.docker.com/install/). Then :

### Install

```sh
# Download camptocamp.org source code :
git clone https://github.com/c2corg/v6_api
cd v6_api

# Build dev env. It's quite long, but you have to do it once.
docker-compose build
```

### Run

```sh
docker-compose up
```

:heart: <http://localhost:6543> :heart:

Press CTRL+C to terminate it.

### Run the background jobs and syncer scripts

In distinct terminals:

```sh
docker-compose exec api make -f config/docker-dev run-background-jobs
docker-compose exec api make -f config/docker-dev run-syncer
```

### Check code quality

In another terminal (`docker-compose up` must be running) :

```sh
docker-compose exec api make -f config/docker-dev lint
```

### Run test suite 

In another terminal (`docker-compose up` must be running) :

```sh
# First, inititate test database, must be done once
docker-compose exec postgresql /v6_api/scripts/create_user_db_test.sh

# Then
docker-compose exec api make -f config/docker-dev test
```

## Useful links in [wiki](https://github.com/c2corg/v6_api/wiki)

[Full info about development environment](https://github.com/c2corg/v6_api/wiki/Development-environment-on-Linux)
