# Open the file in write mode (it will create the file if it doesn't exist)
with open('.buffer', 'w', buffering=1) as file:
    # Keep taking input from the user until they type 'exit'
    while True:
        user_input = input("Enter text (type 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        file.write(user_input + '\n')  # Write the input to the file
        file.flush()
    print("All inputs have been written to .buffer file.")
