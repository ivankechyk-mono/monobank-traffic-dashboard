BUSINESS_PATH_PREFIX = "/business/"

PRODUCT_URL_PATTERNS = {
    "ЮО": ["/business/card", "/business/account", "/business/current"],
    "ФОП": ["/business/fop"],
    "Еквайринг": ["/business/acquiring"],
    "ЗП-проект": ["/business/salary"],
}

WEEKS_TO_KEEP = 40


def get_product_by_url(page_path: str) -> str:
    for product, patterns in PRODUCT_URL_PATTERNS.items():
        for pattern in patterns:
            if page_path.startswith(pattern):
                return product
    return "Unknown product"
