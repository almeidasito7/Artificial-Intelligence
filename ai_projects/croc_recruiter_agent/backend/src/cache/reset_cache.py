from src.cache.cache_repository import CacheRepository


def main():
    print("Resetting semantic cache...")

    cache = CacheRepository()
    cache.reset_table()

    print("Cache ready!")


if __name__ == "__main__":
    main()