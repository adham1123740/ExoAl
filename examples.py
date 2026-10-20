from exoal import ExoAl, ExoAlError

API_URL = "https://dev-vnk.pantheonsite.io/api.php"

def main():
    ai = ExoAl(API_URL, model="qwen3-8b")
    try:
        print("Models:")
        for item in ai.models():
            print(f"- {item['id']}: {item['name']}")
        print(ai.set_model("qwen3-8b"))
        print(ai.chat("Hello from ExoAl", stream=False))
    except ExoAlError as exc:
        print(f"API error: {exc}")
    finally:
        ai.close()

if __name__ == "__main__":
    main()
