# Corta.ai — V1 Real

Base própria inspirada no fluxo de auto-clipping open source. A implementação deste pacote é organizada para Corta.ai e não depende de API paga de IA para o fluxo principal.

## O que funciona

- Interface Corta.ai sem login.
- Upload de vídeo.
- Link do YouTube.
- Download do vídeo via yt-dlp no servidor.
- Transcrição local com Faster-Whisper.
- Análise NLP heurística de hooks e trechos.
- Seleção automática de cortes.
- FFmpeg para renderização.
- 9:16, 1:1 e 16:9.
- Legendas SRT queimadas no vídeo quando a transcrição estiver disponível.
- MP4 H.264.
- Progresso do job.
- Download de cada corte.
- Docker.
- Render Blueprint.

## Rodar localmente

```bash
docker build -t corta-ai .
docker run -p 5000:5000 corta-ai
```

Abra `http://localhost:5000`.

## Deploy

O projeto foi preparado para um serviço Docker. O `render.yaml` usa um plano pago porque processamento de vídeo + Whisper + armazenamento persistente não é algo que eu possa prometer como gratuito de forma confiável.

No Render:
1. Crie um repositório GitHub com estes arquivos.
2. New + → Blueprint.
3. Selecione o repositório.
4. O Render lê `render.yaml`.
5. Faça o deploy.

## Observação importante sobre YouTube

Use somente vídeos que você tenha autorização/direitos para baixar e processar. O Corta.ai não deve ser usado para contornar controles de acesso ou direitos autorais.

## IA sem API

O fluxo principal usa Faster-Whisper localmente. A escolha de trechos usa análise local. Nenhuma chave de OpenAI, Gemini ou Groq é necessária.

Uma futura versão pode oferecer um LLM opcional como segunda camada de pontuação.

## Limitações V1

- O processamento é CPU e pode ser lento em vídeos longos.
- `tiny` é escolhido para reduzir consumo; um modelo maior pode melhorar a transcrição.
- O worker atual é simples e mantém jobs em memória. Para produção com muitos usuários, a próxima etapa deve usar fila (Redis/RQ/Celery) e armazenamento de objetos.
- O armazenamento local depende do disco da plataforma.

## Licença do Corta.ai

Este pacote contém código desenvolvido para o projeto Corta.ai. Dependências de terceiros continuam sob suas respectivas licenças.
