#!/bin/bash
NAME=$1
curl http://localhost:8080/models/apply -H "Content-Type: application/json" -d '{
     "url": "https://raw.githubusercontent.com/go-skynet/model-gallery/main/${NAME}.yaml",
     "name": "${NAME}"
   }'  
