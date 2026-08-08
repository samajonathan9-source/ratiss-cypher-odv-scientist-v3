FROM python:3.11-slim

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl bash nodejs npm && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Python : interface Open Views
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Node : Prime Agent (npm global, fiable dans Docker ; fallback sur l'installateur officiel)
RUN npm install -g prime-agent --yes 2>/dev/null || \
    ( mkdir -p /tmp/pa && cd /tmp/pa && \
      curl -fsSL -o install.sh https://app.primeintellect.ai/prime-agent/install.sh && \
      printf 'Y\nY\nY\nY\nY\nY\n' | script -qec "sh install.sh" /dev/null > /dev/null 2>&1 ) ; \
    rm -rf /tmp/pa

COPY . .

ENV PYTHONUNBUFFERED=1
ENV MEMORY_GUARD_MB=7500
ENV PRIME_AGENT_PROVIDER=openrouter
ENV PRIME_AGENT_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
ENV PRIME_AGENT_TIMEOUT=900

# Secrets HF Spaces (OpenRouter, HF, IBM, Quandela) injectés par HF en variables d'environnement

EXPOSE 7860
CMD ["uvicorn", "interface.app:app", "--host", "0.0.0.0", "--port", "7860"]
