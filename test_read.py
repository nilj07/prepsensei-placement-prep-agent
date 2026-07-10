from utils import read_resume
# Make sure you put your exact resume filename here
text = read_resume("your_resume_name.pdf") 
print("--- RAW TEXT FROM PDF ---")
print(text[:1000]) # Print first 1000 characters