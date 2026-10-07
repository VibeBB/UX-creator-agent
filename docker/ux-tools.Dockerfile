ARG UV_VERSION=0.12.23
ARG UV_DIGEST=sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21
FROM ghcr.io/astral-sh/uv:${UV_VERSION}@${UV_DIGEST} AS uv

# ruby:4.0.7-slim-trixie — Debian 13 with Ruby 4.0.7 (YJIT+ZJIT).
FROM ruby:4.0.7-slim-trixie@sha256:d10bdb076bb10d2261773ea20eadf4cdbde3346fc8f8db409856608b2d01b9c9

ARG DEBIAN_FRONTEND=noninteractive
ARG UV_VERSION=0.12.23
ARG IMAGE_REVISION=unknown
ARG SEMERU_JRE_VERSION=27.0.0.0
ARG SEMERU_JRE_SHA256=9e6d9c1131da124bd08eb4183f7787a9f90111fc3d62c1231976c2d37372d59e
ARG PLANTUML_VERSION=1.2026.8
ARG PLANTUML_SHA256=3629c9cd017c7f73e6450396eea0040216c7e1eef8473ce33cc1aad469dab2f9
ARG MRUBY_VERSION=4.0.0
ARG MRUBY_SHA256=e2ea271dbed14e9f2b33df773ae447b747dbc242ce2675022c0a57efea85a7b4
ARG NODE_VERSION=26.11.0
# sha256 of https://nodejs.org/dist/v26.11.0/node-v26.11.0-linux-x64.tar.xz
ARG NODE_SHA256=db6342d36ebdb3cbd72103d0ce5ccc528620f6c9df72a11f4ccb384bf1bef678
ARG MERMAID_CLI_VERSION=12.0.0
# sha256 of https://registry.npmjs.org/@mermaid-js/mermaid-cli/-/mermaid-cli-12.0.0.tgz
ARG MERMAID_CLI_SHA256=b5b43bc60c2e6bc87f7d12ab3e6e78883c799213ea5b015363fecdd5e6363c84
ARG RUBOCOP_VERSION=1.91.0
ARG MINITEST_VERSION=6.0.6
ARG JSON_VERSION=3.0.2

# Fail the build when the left side of a verification pipe (curl|sha256sum)
# breaks instead of silently passing the right side.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
ENV JAVA_HOME=/opt/jre
ENV PLANTUML_JAR=/opt/plantuml/plantuml.jar
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_CONFIG=/opt/ux/docker/puppeteer-config.json
ENV PATH="/opt/mruby/bin:/opt/jre/bin:/usr/local/bundle/bin:/opt/ux/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
# Keep runtime bytecode caches out of the root-owned /opt/ux tree so the
# non-root `ux` user does not need write access to the sources.
ENV PYTHONPYCACHEPREFIX=/tmp/ux-pycache

LABEL org.opencontainers.image.source="https://github.com/VibeBB/UX-creator-agent" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.revision="${IMAGE_REVISION}" \
      ux.uv.version="${UV_VERSION}" \
      ux.semeru.version="${SEMERU_JRE_VERSION}" \
      ux.plantuml.version="${PLANTUML_VERSION}" \
      ux.mruby.version="${MRUBY_VERSION}" \
      ux.node.version="${NODE_VERSION}" \
      ux.mermaid-cli.version="${MERMAID_CLI_VERSION}"

COPY --from=uv /uv /uvx /usr/local/bin/

RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install --no-install-recommends -y \
        ca-certificates \
        curl \
        git \
        graphviz \
        fontconfig \
        fonts-ipafont \
        fonts-noto-cjk \
        build-essential \
        bison \
        chromium \
        xz-utils \
        # Ships in the digest-pinned base image; listed so apt upgrades it to
        # the security build (CVE-2026-103111, fixed in 10.46-1~deb13u3).
        libpcre2-8-0 \
    && rm -rf /var/lib/apt/lists/*

# Node.js official tarball — Debian trixie ships nodejs 20.x, which blocks
# mermaid-cli 12 (needs Node >=22.13). Installed from a sha256-verified
# nodejs.org tarball, the same verified-download pattern as the other tools.
# Provides /usr/local/bin/{node,npm,npx,corepack} (npm is bundled).
RUN curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /tmp/node.tar.xz \
        "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    && echo "${NODE_SHA256}  /tmp/node.tar.xz" | sha256sum --check \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 --no-same-owner \
    && rm -f /tmp/node.tar.xz \
    && node --version | grep -F "v${NODE_VERSION}" \
    && npm --version \
    && mkdir -p /usr/share/doc/node \
    && printf '%s\n' \
        "source=https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
        "version=v${NODE_VERSION}" \
        > /usr/share/doc/node/SOURCE

# Install mermaid-cli from the registry tarball so the fetch is
# sha256-verified like every other external download in this image.
RUN curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /tmp/mermaid-cli.tgz \
        "https://registry.npmjs.org/@mermaid-js/mermaid-cli/-/mermaid-cli-${MERMAID_CLI_VERSION}.tgz" \
    && echo "${MERMAID_CLI_SHA256}  /tmp/mermaid-cli.tgz" | sha256sum --check \
    && npm install -g /tmp/mermaid-cli.tgz \
    && rm -f /tmp/mermaid-cli.tgz \
    && mmdc --version

# IBM Semeru OpenJ9 JRE (for PlantUML) — same verified pattern as
# electrical-circuit-agent's circuit-tools image.
RUN mkdir -p /opt/jre \
    && curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /tmp/semeru-jre.tar.gz \
        "https://github.com/ibmruntimes/semeru27-binaries/releases/download/jdk-${SEMERU_JRE_VERSION}/ibm-semeru-open-jre_x64_linux_${SEMERU_JRE_VERSION}.tar.gz" \
    && echo "${SEMERU_JRE_SHA256}  /tmp/semeru-jre.tar.gz" | sha256sum --check \
    && tar -xzf /tmp/semeru-jre.tar.gz -C /opt/jre --strip-components=1 \
    && rm -f /tmp/semeru-jre.tar.gz \
    && command -v java | grep -E '^/opt/jre/bin/java$' \
    && java -version 2>&1 | grep -q 'Eclipse OpenJ9 VM' \
    && java -version 2>&1 | grep -F "IBM Semeru Runtime Open Edition ${SEMERU_JRE_VERSION}" \
    && mkdir -p /usr/share/doc/semeru-jre \
    && printf '%s\n' \
        "source=https://github.com/ibmruntimes/semeru27-binaries" \
        "version=jdk-${SEMERU_JRE_VERSION}" \
        > /usr/share/doc/semeru-jre/SOURCE

# PlantUML MIT jar (GitHub releases; Maven Central rate-limits CI).
RUN mkdir -p /opt/plantuml \
    && curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /opt/plantuml/plantuml.jar \
        "https://github.com/plantuml/plantuml/releases/download/v${PLANTUML_VERSION}/plantuml-mit-${PLANTUML_VERSION}.jar" \
    && echo "${PLANTUML_SHA256}  /opt/plantuml/plantuml.jar" | sha256sum --check \
    && java -jar /opt/plantuml/plantuml.jar -version 2>&1 | grep -F "PlantUML" \
    && mkdir -p /usr/share/doc/plantuml \
    && curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /usr/share/doc/plantuml/LICENSE \
        "https://raw.githubusercontent.com/plantuml/plantuml/v${PLANTUML_VERSION}/LICENSE" \
    && printf '%s\n' \
        "source=https://github.com/plantuml/plantuml (mit jar)" \
        "version=v${PLANTUML_VERSION}" \
        > /usr/share/doc/plantuml/SOURCE

# mruby built from the pinned source tarball (embedded-firmware UX checks).
RUN curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /tmp/mruby.tar.gz \
        "https://github.com/mruby/mruby/archive/refs/tags/${MRUBY_VERSION}.tar.gz" \
    && echo "${MRUBY_SHA256}  /tmp/mruby.tar.gz" | sha256sum --check \
    && tar -xzf /tmp/mruby.tar.gz -C /tmp \
    && ruby -C"/tmp/mruby-${MRUBY_VERSION}" ./minirake -j"$(nproc)" \
    && mkdir -p /opt/mruby/bin \
    && install -m 0755 \
        "/tmp/mruby-${MRUBY_VERSION}/build/host/bin/mruby" \
        "/tmp/mruby-${MRUBY_VERSION}/build/host/bin/mrbc" \
        "/tmp/mruby-${MRUBY_VERSION}/build/host/bin/mirb" \
        /opt/mruby/bin/ \
    && mruby --version | grep -F "mruby" \
    && rm -rf "/tmp/mruby-${MRUBY_VERSION}" /tmp/mruby.tar.gz \
    && mkdir -p /usr/share/doc/mruby \
    && printf '%s\n' \
        "source=https://github.com/mruby/mruby" \
        "version=${MRUBY_VERSION}" \
        > /usr/share/doc/mruby/SOURCE

# The base image ships json 2.18.0 as a default gem (CVE-2026-33210). Install
# the fixed release, then remove every 2.18.0 trace — the default gemspec that
# Trivy flags plus the stdlib copies that would otherwise shadow the update.
RUN rm -f /usr/local/lib/ruby/gems/*/specifications/default/json-*.gemspec \
    && rm -rf /usr/local/lib/ruby/gems/*/gems/json-* \
              /usr/local/lib/ruby/*/json.rb \
              /usr/local/lib/ruby/*/json \
              /usr/local/lib/ruby/*/x86_64-linux/json \
    && gem install "json:${JSON_VERSION}" --no-document \
    && gem install "rubocop:${RUBOCOP_VERSION}" "minitest:${MINITEST_VERSION}" --no-document \
    && rubocop --version | grep -F "${RUBOCOP_VERSION}" \
    && ruby -rjson -e 'exit 1 unless JSON::VERSION == ENV.fetch("JSON_VERSION")'

# The uv-managed CPython bundles pip with vendored copies of urllib3,
# msgpack, and setuptools that nothing in the image invokes — dependencies
# install via uv and the shipped venv is pip-less — so strip the payload
# instead of shipping unused vulnerable vendored packages.
RUN uv python install 3.14 \
    && rm -rf /opt/uv-python/bin/pip* \
              /opt/uv-python/cpython-*/bin/pip* \
              /opt/uv-python/cpython-*/lib/python3.*/site-packages/pip \
              /opt/uv-python/cpython-*/lib/python3.*/site-packages/pip-*.dist-info \
              /opt/uv-python/cpython-*/lib/python3.*/ensurepip \
              /root/.cache/uv \
    && uv venv --python 3.14 /opt/ux/.venv

COPY pyproject.toml uv.lock /opt/ux/
COPY src /opt/ux/src
COPY plugins/ux /opt/ux/plugins/ux
COPY ruby /opt/ux/ruby
COPY scripts/e2e_authoring.py /opt/ux/scripts/e2e_authoring.py
COPY scripts/check_ruby_dsl.py /opt/ux/scripts/check_ruby_dsl.py
COPY examples /opt/ux/examples
COPY docker/puppeteer-config.json /opt/ux/docker/puppeteer-config.json

WORKDIR /opt/ux

RUN uv export --frozen --no-dev --no-emit-project --format requirements-txt \
        --output-file /tmp/ux-requirements.txt \
    && uv pip install --python /opt/ux/.venv/bin/python \
        --requirement /tmp/ux-requirements.txt \
    && uv pip install --python /opt/ux/.venv/bin/python --no-deps /opt/ux \
    && python -c "import ux_creator, pydantic; print(ux_creator.__version__)" \
    && python -m ux_creator doctor \
    && rm -f /tmp/ux-requirements.txt

# Tighten the login.defs umask to 027 (Lynis AUTH-9328): the image has no
# interactive users, so files created at runtime stay group-readable only.
RUN printf 'UMASK 027\n' >> /etc/login.defs

RUN if ! getent group ux >/dev/null; then groupadd ux; fi \
    && if getent passwd 1000 >/dev/null; then \
         existing="$(getent passwd 1000 | cut -d: -f1)"; \
         if [ "$existing" != ux ]; then usermod --login ux --gid ux "$existing"; fi; \
         usermod --home /home/ux ux; \
       else \
         useradd --uid 1000 --gid ux --create-home --shell /bin/bash ux; \
       fi \
    && mkdir -p /home/ux/.cache \
    && chown -R ux:ux /home/ux

USER ux

# Build-time smoke: ruby DSL -> contract -> author -> gates pass; mruby,
# mermaid-cli and plantuml verified end to end.
RUN ruby /opt/ux/ruby/bin/ux-dsl /opt/ux/examples/smart-kettle/smart-kettle.ux.rb \
      > /tmp/smart-kettle.ux.json \
    && diff -u /opt/ux/examples/smart-kettle/smart-kettle.ux.json /tmp/smart-kettle.ux.json \
    && python /opt/ux/scripts/e2e_authoring.py \
      --contract /opt/ux/examples/smart-kettle/smart-kettle.ux.json \
      --out /tmp/smoke-out --render \
    && python - <<'PY'
import json
report = json.load(open("/tmp/smoke-out/ux-report.json", encoding="utf-8"))
assert report["verdict"] == "pass", report
print("image smoke check: verdict pass")
PY

RUN ruby -w -c /opt/ux/ruby/lib/ux_dsl.rb \
    && rubocop --config /opt/ux/ruby/.rubocop.yml /opt/ux/ruby \
    && ruby -I /opt/ux/ruby/lib /opt/ux/ruby/test/ux_dsl_test.rb \
    && printf 'class Smoke; def ok? = true; end\n' > /tmp/smoke.rb \
    && mrbc -c /tmp/smoke.rb \
    && printf 'journey\n  title smoke\n  section s\n    t: 5: user\n' > /tmp/smoke.mmd \
    && mmdc -i /tmp/smoke.mmd -o /tmp/smoke.svg -b transparent -p /opt/ux/docker/puppeteer-config.json \
    && test -s /tmp/smoke.svg \
    && java -jar /opt/plantuml/plantuml.jar -testdot \
    && printf '@startuml\n[*] --> a\na --> b : go\nb --> [*]\n@enduml\n' > /tmp/smoke.puml \
    && java -jar /opt/plantuml/plantuml.jar -tsvg -output /tmp /tmp/smoke.puml \
    && test -s /tmp/smoke.svg \
    && rm -rf /tmp/smoke*
