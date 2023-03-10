print("This is a simple example to show you how to run code inside docker")
print(
    "\nWe will try now to import numpy to verify that your image was built correctly."
)
try:
    print("Importing numpy...")
    import numpy as np

    print("Successfully imported numpy!")
    print("Testing numpy...")
    result = np.array([1]) + np.array([1])
    print(f"np.array([1]) + np.array([1]) = {result}")
except Exception as exception:
    print("Failed to import numpy, your docker image is not correctly built")
    quit()

print("\nIf you see this message, you have done things right!")
print("=)")
