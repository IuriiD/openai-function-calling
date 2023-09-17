import openai
import json
import os
from dotenv import load_dotenv
import requests
import argparse

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

parser = argparse.ArgumentParser()
requiredNamed = parser.add_argument_group('required arguments')

requiredNamed.add_argument('--query',
                           help='Write the foods for which nutrients data needs to be found and whether this info should be saved to Airflow',
                           required=True)

args = parser.parse_args()

query = args.query


def call_openai_completion(query):
    messages = [{"role": "user", "content": query}]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    print(response)


call_openai_completion(query)
