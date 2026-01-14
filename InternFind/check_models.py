import google.generativeai as genai
import os


api_key = "AIzaSyChyZgr8G69ZaHonO18hNBJFUqLQkyQ4Jk" 

genai.configure(api_key=api_key)

print("Listing available models...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)