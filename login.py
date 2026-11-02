# used only by hand to get the token.json

from auth import GoogleAuthManager

def main():
	manager = GoogleAuthManager()
	manager.login()

if __name__ == "__main__":
	main()