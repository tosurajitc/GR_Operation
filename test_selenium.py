try:
    from selenium import webdriver
    print('Selenium imported successfully!')
    print(f'Selenium version: {webdriver.__version__}')
except ImportError as e:
    print(f'Error importing selenium: {e}')