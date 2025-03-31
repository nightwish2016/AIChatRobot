from openai import OpenAI
client = OpenAI(api_key='xxx')
# client.

# response = client.images.generate(
#   model="dall-e-3",
#   prompt="a beautiful chinese girl ",
#   size="1024x1024",
#   quality="standard",
#   n=1,
# )
response = client.images.generate(
  model="dall-e-2",
  prompt="a beautiful chinese girl ",
  size="256x256",
  quality="standard",
  n=2,
)
print(response)
image_url = response.data[0].url
print(image_url)