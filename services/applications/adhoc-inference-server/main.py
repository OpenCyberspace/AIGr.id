from core import ai_server, rest

def main():
    # start REST control server:
    rest.run_app()
    ai_server.serve()

if __name__ == "__main__":
    main()

        