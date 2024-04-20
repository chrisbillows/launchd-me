def main():
    print("I am main, will I work again???")
    with open("/Users/chrisbillows/Documents/CODE/MY_GITHUB_REPOS/launchd-me/src/launchd_me/templates/plist_template.txt") as file_handle:
        content = file_handle.readlines()
        print(content[12])

if __name__ == "__main__":
    main()
