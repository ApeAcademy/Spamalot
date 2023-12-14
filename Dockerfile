FROM python:3.10 AS base

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Create virtualenv using poetry lockfile
FROM base AS builder

ENV PIP_NO_CACHE_DIR=off \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.6.1

RUN pip install eth-ape ape-vyper

COPY dropbot/ape-config.yaml ape-config.yaml
COPY dropbot/contracts/erc721.vy contracts/erc721.vy

RUN ape compile

RUN ls -lah .build

FROM apeworx/silverback:latest

WORKDIR  /app

# install and git
USER root
RUN apt-get -y update && apt-get -y install git

# Install Necessary plugins for chaosnet environment
RUN pip install asyncer

# Install Silverback private plugin
RUN ssh-keyscan -H github.com >> /etc/ssh/ssh_known_hosts
RUN --mount=type=ssh,id=github_ssh_key \
    pip install "git+ssh://git@github.com/ApeWorX/ape-silverback@main#egg=ape_silverback"

USER harambe

# Copy the app into the container
COPY --chown=harambe:harambe dropbot/scripts/bot.py bot.py

# Copy artficats used to init contracts
COPY --from=builder --chown=harambe:harambe /build/contracts/erc721.vy contracts/erc721.vy
COPY --from=builder --chown=harambe:harambe /build/.build/__local__.json .build/__local__.json
COPY --from=builder --chown=harambe:harambe /build/.build/erc721.json .build/erc721.json

CMD ["run", "bot:app", "--network", "::foundry", "--account", "bot"]
