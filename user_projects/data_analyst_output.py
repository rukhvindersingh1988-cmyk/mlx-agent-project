from statistics import mean, median, multimode

def calculate_stats(data):
    mean_value = mean(data)
    median_value = median(data)
    mode_value = multimode(data)
    return mean_value, median_value, mode_value

# Example usage:
numbers = [1, 2, 3, 4, 4, 5, 5, 5]
mean_val, median_val, mode_val = calculate_stats(numbers)
print(f"Mean: {mean_val}, Median: {median_val}, Mode: {mode_val}")