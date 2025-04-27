from email_chatbot import email_bot

def main():
    print("Email Bot CLI")
    print("Type 'exit' to quit")
    print("-" * 50)
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            # Process the input through email_bot
            response = email_bot(user_input)
            
            # Print the response
            print("\nBot:", response)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Please try again.")

if __name__ == "__main__":
    main() 