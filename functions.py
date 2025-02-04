import openai

class GenerateImage:
    definition = {
        "name": "generate_image",
        "description": "Generate an image based on a given prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A description of the image to be generated.",
                }
            },
            "required": ["prompt"]
        }
    }

    def function(self, prompt):
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
