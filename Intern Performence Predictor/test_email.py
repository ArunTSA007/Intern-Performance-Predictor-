from email_utils import send_registration_email

# TEST CONFIGURATION
TEST_RECEIVER = "your-receiving-email@example.com" # Change this to your own email to test
TEST_NAME = "Test Intern"
TEST_COURSE = "Python Development"

print("--- Email SMTP Test ---")
print(f"Testing with receiver: {TEST_RECEIVER}")

success = send_registration_email(TEST_RECEIVER, TEST_NAME, TEST_COURSE)

if success:
    print("\n✅ SUCCESS: The email was sent successfully!")
else:
    print("\n❌ FAILURE: Check the error message above for details.")
    print("\nCommon fixes:")
    print("1. Ensure SENDER_EMAIL and SENDER_PASSWORD (App Password) are correct in email_utils.py.")
    print("2. If using Gmail, you MUST use an 'App Password', NOT your regular account password.")
    print("3. Ensure your internet connection allows outgoing SMTP traffic (Port 587).")
