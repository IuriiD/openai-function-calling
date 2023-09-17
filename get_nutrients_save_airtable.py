import openai
import json
import os
from dotenv import load_dotenv
from pyairtable import Table
import requests
import argparse

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
airtable_api_key = os.getenv("AIRTABLE_API_KEY")
nutritionix_app_id = os.getenv("NUTRITIONIX_APP_ID")
nutritionix_api_key = os.getenv("NUTRITIONIX_API_KEY")

table = Table(airtable_api_key, "appnAsa5kDIKs6ZHZ", "tblWavC1dmC9Uc15D")

parser = argparse.ArgumentParser()
requiredNamed = parser.add_argument_group('required arguments')

requiredNamed.add_argument('--query',
                           help='Write the foods for which nutrients data needs to be found and whether this info should be saved to Airflow',
                           required=True)

args = parser.parse_args()

query = args.query

function_descriptions = [
    {
        "name": "get_nutrition_data",
        "description": "Gets nutrition data, e.g. calories, fat, protein, carbohydrates content in a given food",
        "parameters": {
            "type": "object",
            "properties": {
                "meal": {
                    "type": "string",
                    "description": "foods consumed and their quantity",
                    "example": "1 egg and a slice of bread"
                }
            },
            "required": ["meal"]
        }
    },
    {
        "name": "add_meal_data_airtable",
        "description": "Adds the meal consumed and nutrition facts about it to Airtable",
        "parameters": {
            "type": "object",
            "properties": {
                "foods": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "meal": {
                                "type": "string",
                                "description": "meal name"
                            },
                            "calories": {
                                "type": "number",
                                "description": "kilocalorie (kcal) content in the consumed dish"
                            },
                            "fat": {
                                "type": "number",
                                "description": "fat content (g) in the consumed dish"
                            },
                            "protein": {
                                "type": "number",
                                "description": "protein content (g) in the consumed dish"
                            },
                            "carbohydrate": {
                                "type": "number",
                                "description": "carbohydrate content (g) in the consumed dish"
                            },
                            "food_image": {
                                "type": "string",
                                "description": "link to an image of the food"
                            }
                        },
                        "required": ["meal", "calories", "fat", "protein", "carbohydrate"]
                    }
                }
            },
            "required": ["foods"]
        }
    }
]


def add_meal_data_airtable(foods):
    print('\n>>> Calling ADD_MEAL_DATA_AIRTABLE()')
    print("\n>>> foods", foods)

    for food in foods:
        meal = food["meal"]
        kcal = food["calories"]
        fat = food["fat"]
        protein = food["protein"]
        carbohydrate = food["carbohydrate"]
        food_image = food["food_image"]
        table.create({"meal": meal, "kcal": kcal, "fat, g": fat, "protein, g": protein, "carbohydrates, g": carbohydrate, "food_image": food_image})


def extract_each_food_data(food):
    food_name = food["food_name"]
    serving_qty = food["serving_qty"]
    serving_unit = food["serving_unit"]
    nf_calories = food["nf_calories"]
    nf_total_fat = food["nf_total_fat"]
    nf_total_carbohydrate = food["nf_total_carbohydrate"]
    nf_protein = food["nf_protein"]
    food_image = food["photo"]["thumb"]

    str_res = f'{food_name} ({serving_qty} {serving_unit}): {nf_calories} kcal, {nf_total_fat} g fat, {nf_total_carbohydrate} g carbohydrates, {nf_protein} g protein, photo - {food_image}'
    print('\n>>> Response from extract_each_food_data(): \n', str_res)

    return {
        "meal": f'{food_name} ({serving_qty} {serving_unit})',
        "calories": nf_calories,
        "fat": nf_total_fat,
        "protein": nf_protein,
        "carbohydrate": nf_total_carbohydrate,
        "food_image": food_image
        }


def get_nutrition_data(meal):
    print('\n>>> Calling GET_NUTRITION_DATA()')
    url = "https://trackapi.nutritionix.com/v2/natural/nutrients"

    data = {"query": meal}

    headers = {
        "x-app-id": nutritionix_app_id,
        "x-app-key": nutritionix_api_key,
        "x-remote-user-id": '0'  # user id, 0 if testing
    }

    api_res = requests.post(url, headers=headers, data=data).json()

    foods = []
    for food in api_res["foods"]:
        this_food_data = extract_each_food_data(food)
        foods.append(this_food_data)
    food = api_res["foods"][0]

    return foods


def function_call(ai_response):
    function_call = ai_response["choices"][0]["message"]["function_call"]
    function_name = function_call["name"]
    arguments = function_call["arguments"]
    if function_name == "get_nutrition_data":
        meal = eval(arguments).get("meal")
        return get_nutrition_data(meal)
    elif function_name == "add_meal_data_airtable":
        foods = eval(arguments).get("foods")
        return add_meal_data_airtable(foods=foods)
    else:
        return


def ask_function_calling(query):
    messages = [{"role": "user", "content": query}]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        functions=function_descriptions,
        function_call="auto"
    )

    print('\n\n>>>> After the initial call:')
    print(response)

    while response["choices"][0]["finish_reason"] == "function_call":
        function_response = function_call(response)
        messages.append({
            "role": "function",
            "name": response["choices"][0]["message"]["function_call"]["name"],
            "content": json.dumps(function_response)
        })

        print('\n\n>>>> Got "function_call, next prompt to LLM":')
        print(messages)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            functions=function_descriptions,
            function_call="auto"
        )

        print('\n\n>>>> After calling LLM with data from the prev. function call:')
        print("response: ", response)
    else:
        print('\n\n>>>> Got NOT a "function_call":')


ask_function_calling(query)
