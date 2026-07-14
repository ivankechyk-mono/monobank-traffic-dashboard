WEEKS_TO_KEEP = 40

BUSINESS_PAGES = [
    "/business",
    "/fop",
    "/acquiring",
    "/chast/vendors",
    "/advance",
    "/qr-sign",
    "/payment-link",
    "/terminal",
    "/pos",
    "/plata-by-mono",
    "/mini-site",
    "/beauty",
    "/events",
    "/insta-shops",
    "/ecomm",
    "/subscription-services",
    "/creators",
    "/knowledge-base",
    "/documents",
    "/api-docs",
]

PRODUCT_URL_PATTERNS = {
    "ЮО": ["/business/account", "/business/current", "/business-account"],
    "ФОП": ["/business/fop", "/fop"],
    "Еквайринг": ["/business/acquiring", "/acquiring", "/plata-by-mono", "/pos", "/terminal", "/qr-sign", "/payment-link"],
    "ЗП-проект": ["/business/salary"],
    "Пакети": ["/beauty", "/events", "/insta-shops", "/ecomm", "/subscription-services", "/creators"],
    "Аванс": ["/advance"],
    "Частинами": ["/chast/vendors"],
}


def get_product_by_url(page_path: str) -> str:
    for product, patterns in PRODUCT_URL_PATTERNS.items():
        for pattern in patterns:
            if page_path.startswith(pattern):
                return product
    return "Unknown product"


def is_business_page(page_path: str) -> bool:
    return any(page_path.startswith(p) for p in BUSINESS_PAGES)
