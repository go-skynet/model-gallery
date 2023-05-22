<h1 align="center">
  <br>
  <img height="300" src="https://github.com/go-skynet/model-gallery/assets/2420543/7a6a8183-6d0a-4dc4-8e1d-f2672fab354e"> <br>
  <a href="https://github.com/go-skynet/LocalAI">LocalAI</a> model gallery
<br>
</h1>

The model gallery is a curated collection of models created by the community and tested with [LocalAI](https://github.com/go-skynet/LocalAI).

We encourage contributions to the gallery! However, please note that if you are submitting a pull request (PR), we cannot accept PRs that include URLs to models based on LLaMA or models with licenses that do not allow redistribution. Nevertheless, you can submit a PR with the configuration file without including the downloadable URL.

## How to install a model

To install a model you will need to use the `/models/apply` LocalAI API endpoint.

<details>

The installation requires the model configuration file URL (`url`), optionally a name to install the model (`name`), extra files to install (`files`), and configuration overrides (`overrides`). When calling the API endpoint, LocalAI will download the models files and write the configuration to the folder used to store models.

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "<MODEL_CONFIG_FILE>",
     "name": "<MODEL_NAME>"
   }'  
```

The API will return a job `uuid` that you can use to track the job progress:
```
{"uuid":"1059474d-f4f9-11ed-8d99-c4cbe106d571","status":"http://localhost:8080/models/jobs/1059474d-f4f9-11ed-8d99-c4cbe106d571"}
```

For instance, a small example bash script that waits a job to complete can be (requires `jq`):

```bash
response=$(curl -s http://localhost:8080/models/apply -H "Content-Type: application/json" -d '{"url": "$model_url"}')

job_id=$(echo "$response" | jq -r '.uuid')

while [ "$(curl -s http://localhost:8080/models/jobs/"$job_id" | jq -r '.processed')" != "true" ]; do 
  sleep 1
done

echo "Job completed"
```

</details>

### Additional Files

<details>

To download additional files with the model, use the `files` parameter:

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "<MODEL_CONFIG_FILE>",
     "name": "<MODEL_NAME>",
     "files": [
        {
            "uri": "<additional_file_url>",
            "sha256": "<additional_file_hash>",
            "filename": "<additional_file_name>"
        }
     ]
   }'  
```

</details>

### Overriding configuration files

<details>

To override portions of the configuration file, such as the backend or the model file, use the `overrides` parameter:

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "<MODEL_CONFIG_FILE>",
     "name": "<MODEL_NAME>",
     "overrides": {
        "backend": "llama"
     }
   }'  
```

</details>

## What if the model isn't here?

<details>

If you don't find the model in the gallery you can try to use the "base" model and provide an URL to LocalAI:

```
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/base.yaml",
     "name": "model-name",
     "files": [
        {
            "uri": "<URL>",
            "sha256": "<SHA>",
            "filename": "model"
        }
     ]
   }'
```

</details>

## Models

Note: replace `$LOCALAI` with your LocalAI API endpoint.

### Embeddings: Bert

<details>

```bash
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/bert-embeddings.yaml",
     "name": "text-embedding-ada-002"
   }'  
```

To test it:

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/v1/embeddings -H "Content-Type: application/json" -d '{
    "input": "Test",
    "model": "text-embedding-ada-002"
  }'
```

</details>

### Image generation: Stable diffusion

<details>

```bash
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{         
     "url": "github:go-skynet/model-gallery/stablediffusion.yaml"
   }'
```

Test it:

```
curl $LOCALAI/v1/images/generations -H "Content-Type: application/json" -d '{
            "prompt": "floating hair, portrait, ((loli)), ((one girl)), cute face, hidden hands, asymmetrical bangs, beautiful detailed eyes, eye shadow, hair ornament, ribbons, bowties, buttons, pleated skirt, (((masterpiece))), ((best quality)), colorful|((part of the head)), ((((mutated hands and fingers)))), deformed, blurry, bad anatomy, disfigured, poorly drawn face, mutation, mutated, extra limb, ugly, poorly drawn hands, missing limb, blurry, floating limbs, disconnected limbs, malformed hands, blur, out of focus, long neck, long body, Octane renderer, lowres, bad anatomy, bad hands, text",
            "mode": 2,  "seed":9000,
            "size": "256x256", "n":2
}'
```
</details>


### Audio transcription: Whisper

<details>

```bash
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{         
     "url": "github:go-skynet/model-gallery/whisper-base.yaml",
     "name": "whisper-1"
   }'
```

</details>

### GPT: Airoboros 13B

<details>

```bash
 curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/airoboros.yaml",
     "name": "gpt-3.5-turbo",
     "overrides": { "parameters": {"model": "airoboros-13B.q5_1.bin" }, "f16": true },
     "files": [
        {
            "uri": "xxx",        
            "sha256": "68ec4f4434ce4b01512506446a816500fa81ad4cde89f4e61d9ce982774bec06", 
            "filename": "airoboros-13B.q5_1.bin"       
        }
     ]
   }'
```

</details>

### GPT: Airoboros 7B

<details>

```bash
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/airoboros.yaml",
     "name": "gpt-3.5-turbo",
     "overrides": { "parameters": {"model": "airoboros-7b-ggml-q8_0.bin" }, "f16": true }, 
     "files": [
        {
            "uri": "xxx",
            "sha256": "a197f49b53865e7e41953ad4d77f2169a6d7d599b21f87bea36858c2d76a0369", 
            "filename": "airoboros-7b-ggml-q8_0.bin"
        }
     ]
   }'
```
</details>

### GPT: GPT4ALL-J

<details>

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/gpt4all-j.yaml",
     "name": "gpt4all-j"
   }'  
```

To test it:

```
curl $LOCALAI/v1/chat/completions -H "Content-Type: application/json" -d '{
     "model": "gpt4all-j", 
     "messages": [{"role": "user", "content": "How are you?"}],
     "temperature": 0.1 
   }'
```

</details>

### GPT: Manticore 13B

This model definition does not contain a URL. It must be provided with the request.

<details>

```
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/manticore.yaml",
     "name": "manticore",
     "overrides": { "parameters": {"model": "Manticore-13B.ggmlv3.q5_1.bin" }, "f16": true }, 
     "files": [
        {
            "uri": "xxxx",                            
            "sha256": "7d2c76516bcfdedc0d6282e3c352e2423964989fc871e21b1922f0f1b8acc1db", 
            "filename": "Manticore-13B.ggmlv3.q5_1.bin" 
        }
     ]
   }'
```

</details>

### GPT: RWKV-7b

<details>

```bash
LOCALAI=http://localhost:8080
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/rwkv-raven-7b.yaml",
     "name": "rwkv"
   }'  
```

To test it:

```bash
curl $LOCALAI/v1/chat/completions -H "Content-Type: application/json" -d '{
     "model": "rwkv",            
     "messages": [{"role": "user", "content": "How are you?"}],
     "temperature": 0.9, "top_p": 0.8, "top_k": 80
   }'
# {"object":"chat.completion","model":"rwkv","choices":[{"message":{"role":"assistant","content":" I am very well! Thank you! How about you?"}}],"usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}}
```

</details>

### GPT: Koala

This model definition does not contain a URL. It must be provided with the request.

<details>

```bash
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/koala.yaml",
     "name": "koala",
     "overrides": { "parameters": {"model": "koala.bin" } },
     "files": [
        {
            "uri": "https://huggingface.co/xxxx",
            "sha256": "xxx",
            "filename": "koala.bin"
        }
     ]
   }'
```

</details>


### GPT: Vicuna

This model definition does not contain a URL. It must be provided with the request.

<details>

```bash
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/vicuna.yaml",
     "name": "vicuna",
     "overrides": { "parameters": {"model": "vicuna" } },
     "files": [
        {
            "uri": "https://huggingface.co/xxxx",
            "sha256": "xxx",
            "filename": "vicuna"
        }
     ]
   }'
```

</details>

### GPT: WizardLM

This model definition does not contain a URL. It must be provided with the request.

<details>

```bash
curl $LOCALAI/models/apply -H "Content-Type: application/json" -d '{
     "url": "github:go-skynet/model-gallery/wizard.yaml",
     "name": "gpt-3.5-turbo",
     "overrides": { "parameters": {"model": "WizardLM-7B-uncensored.ggmlv3.q5_1" } },
     "files": [
        {
            "uri": "https://huggingface.co/xxxx",
            "sha256": "d92a509d83a8ea5e08ba4c2dbaf08f29015932dc2accd627ce0665ac72c2bb2b",
            "filename": "WizardLM-7B-uncensored.ggmlv3.q5_1"
        }
     ]
   }'
```

</details>
