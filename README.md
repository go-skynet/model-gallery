# model-gallery

The model gallery is a curated collection of models created by the community and tested with LocalAI.

We encourage contributions to the gallery! However, please note that if you are submitting a pull request (PR), we cannot accept PRs that include URLs to models based on LLaMA or models with licenses that do not allow redistribution. Nevertheless, you can submit a PR with the configuration file without including the downloadable URL.

## How to install a model

To install a model you will need to use the `/models/apply` LocalAI API endpoint.

The installation requires the model configuration file URL (`url`), optionally a name to install the model (`name`) and extra files to install (`files`)

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "<MODEL_CONFIG_FILE>",
     "name": "<MODEL_NAME>",
     "files": [
        {
            "uri": "<additional_file>",
            "sha256": "<additional_file_hash>",
            "name": "<additional_file_name>"
        }
     ]
   }'  
```

## Bert embeddings

URL: https://raw.githubusercontent.com/go-skynet/model-gallery/main/bert-embeddings.yaml

### Installation

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "https://raw.githubusercontent.com/go-skynet/model-gallery/main/bert-embeddings.yaml",
     "name": "text-embedding-ada-002"
   }'  
```

### Example

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/v1/embeddings -H "Content-Type: application/json" -d '{
    "input": "Test",
    "model": "text-embedding-ada-002"
  }'
```

## GPT4ALL-J

URL: https://raw.githubusercontent.com/go-skynet/model-gallery/main/gpt4all-j.yaml

### Installation

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "https://raw.githubusercontent.com/go-skynet/model-gallery/main/gpt4all-j.yaml",
     "name": "gpt4all-j"
   }'  
```

### Example

```bash
curl $LOCALAI/v1/chat/completions -H "Content-Type: application/json" -d '{
     "model": "gpt4all-j", 
     "messages": [{"role": "user", "content": "How are you?"}],
     "temperature": 0.1 
   }'
```

## RWKV-7b

URL: https://raw.githubusercontent.com/go-skynet/model-gallery/main/rwkv-raven-7b.yaml

### Installation

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "https://raw.githubusercontent.com/go-skynet/model-gallery/main/rwkv-raven-7b.yaml",
     "name": "rwkv"
   }'  
```

### Example

```bash
curl $LOCALAI/v1/chat/completions -H "Content-Type: application/json" -d '{
     "model": "rwkv",            
     "messages": [{"role": "user", "content": "How are you?"}],
     "temperature": 0.9, "top_p": 0.8, "top_k": 80
   }'
# {"object":"chat.completion","model":"rwkv","choices":[{"message":{"role":"assistant","content":" I am very well! Thank you! How about you?"}}],"usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}}
```