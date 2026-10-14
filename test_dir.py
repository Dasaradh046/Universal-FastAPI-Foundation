import os
print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir("."))
print(".env exists:", os.path.exists(".env"))
if os.path.exists(".env"):
    with open(".env", "r") as f:
        lines = f.readlines()
        print("First few lines of .env:")
        for line in lines[:5]:
            print(line.rstrip())
