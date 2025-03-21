with open("secrets.txt", "r") as f:
    secrets = dict(line.strip().split("=") for line in f if "=" in line)



# Инициализация DeepSeek API
print(secrets.get("DEEPSEEK_API_KEY"))

from openai import OpenAI

client = OpenAI(api_key="sk-7de82a56a7aa4459b1c3cd8ee9057a76", base_url="https://api.deepseek.com")




response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)