ARG UV_VERSION=0.12.19
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ruby:4.0.7-slim-trixie — Debian 13 with Ruby 4.0.7 (YJIT+ZJIT).
FROM ruby:4.0.7-slim-trixie@sha256:d10bdb076bb10d2261773ea20eadf4cdbde3346fc8f8db409856608b2d01b9c9

ARG DEBIAN_FRONTEND=noninteractive
ARG UV_VERSION=0.12.19
ARG IMAGE_REVISION=unknown
ARG SEMERU_JRE_VERSION=27.0.0.0
ARG SEMERU_JRE_SHA256=9e6d9c1131da124bd08eb4183f7787a9f90111fc3d62c1231976c2d37372d59e
ARG PLANTUML_VERSION=1.2026.8
ARG PLANTUML_SHA256=3629c9cd017c7f73e6450396eea0040216c7e1eef8473ce33cc1aad469dab2f9
ARG MRUBY_VERSION=4.0.0
ARG MRUBY_SHA256=e2ea271dbed14e9f2b33df773ae447b747dbc242ce2675022c0a57efea85a7b4
ARG MERMAID_CLI_VERSION=12.0.0
ARG RUBOCOP_VERSION=1.91.0
ARG MINITEST_VERSION=6.0.6

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
        nodejs \
        npm \
        xz-utils \
    && npm install -g "@mermaid-js/mermaid-cli@${MERMAID_CLI_VERSION}" \
    && mmdc --version \
    && rm -rf /var/lib/apt/lists/*

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
        "https://raw.githubusercontent.com/plantuml/plantuml/v${PLANTUML_VERSION}/license-mit.txt" || true \
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
    && cd "/tmp/mruby-${MRUBY_VERSION}" \
    && ruby ./minirake -j"$(nproc)" \
    && mkdir -p /opt/mruby/bin \
    && install -m 0755 build/host/bin/mruby build/host/bin/mrbc build/host/bin/mirb /opt/mruby/bin/ \
    && mruby --version | grep -F "mruby" \
    && rm -rf "/tmp/mruby-${MRUBY_VERSION}" /tmp/mruby.tar.gz \
    && mkdir -p /usr/share/doc/mruby \
    && printf '%s\n' \
        "source=https://github.com/mruby/mruby" \
        "version=${MRUBY_VERSION}" \
        > /usr/share/doc/mruby/SOURCE

RUN gem install "rubocop:${RUBOCOP_VERSION}" "minitest:${MINITEST_VERSION}" --no-document \
    && rubocop --version | grep -F "${RUBOCOP_VERSION}"

RUN uv python install 3.12 \
    && uv venv --python 3.12 /opt/ux/.venv

COPY pyproject.toml uv.lock /opt/ux/
COPY src /opt/ux/src
COPY plugins/ux /opt/ux/plugins/ux
COPY ruby /opt/ux/ruby
COPY scripts/e2e_authoring.py /opt/ux/scripts/e2e_authoring.py
COPY scripts/check_ruby_dsl.py /opt/ux/scripts/check_ruby_dsl.py
COPY examples /opt/ux/examples
COPY docker/puppeteer-config.json /opt/ux/docker/puppeteer-config.json

RUN cd /opt/ux \
    && uv export --frozen --no-dev --no-emit-project --format requirements-txt \
        --output-file /tmp/ux-requirements.txt \
    && uv pip install --python /opt/ux/.venv/bin/python \
        --requirement /tmp/ux-requirements.txt \
    && uv pip install --python /opt/ux/.venv/bin/python --no-deps /opt/ux \
    && python -c "import ux_creator, pydantic; print(ux_creator.__version__)" \
    && python -m ux_creator doctor \
    && rm -f /tmp/ux-requirements.txt

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

WORKDIR /opt/ux
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
    && rm -f /tmp/smoke*&& rm -f /tmp/smoke* rm -rf /tmp/smoke*
