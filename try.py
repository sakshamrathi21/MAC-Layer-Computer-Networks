import time
import datetime

# Using time module
current_time = time.time()  # Returns current epoch time in seconds
print(time.ctime(current_time))  # Converts epoch time to human-readable format

# Using datetime module
current_time = datetime.datetime.now()  # Returns current system time
print(current_time.strftime('%H:%M:%S'))
