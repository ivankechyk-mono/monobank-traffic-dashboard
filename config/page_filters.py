WEEKS_TO_KEEP = 40

# Маркетингові сторінки monobank.ua/business
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
    "/beauty",
    "/events",
    "/insta-shops",
    "/ecomm",
    "/subscription-services",
    "/creators",
    "/knowledge-base",
    "/documents",
    "/api-docs",
    # англомовні версії (/en/*)
    "/en/business",
    "/en/fop",
    "/en/acquiring",
    "/en/advance",
    "/en/qr-sign",
    "/en/payment-link",
    "/en/terminal",
    "/en/pos",
    "/en/plata-by-mono",
    "/en/api-docs",
]

# Кабінетні сторінки web.monobank.ua (бізнес-кабінет)
CABINET_PAGES = [
    "/mono-business",
    "/corp/client",
    "/acquiring-onboard",
    "/acquiring-t2p-onboard",
    "/fop/onboarding",
    "/qr",
]

# (url_prefix, product, sub_product) — порядок важливий: довші префікси першими
URL_PRODUCT_MAP = [
    # маркетингові
    ("/business/salary",              "ЗП-проект",    "ЗП-проект"),
    ("/business/account",             "ЮО",           "Розрахунковий рахунок"),
    ("/business/current",             "ЮО",           "Розрахунковий рахунок"),
    ("/business-account",             "ЮО",           "Розрахунковий рахунок"),
    ("/business/fop",                 "ФОП",          "Відкрити ФОП"),
    ("/fop",                          "ФОП",          "Відкрити ФОП"),
    ("/plata-by-mono",                "Еквайринг",    "Plata by mono (QR)"),
    ("/qr-sign",                      "Еквайринг",    "Plata by mono (QR)"),
    ("/pos",                          "Еквайринг",    "POS-термінал"),
    ("/terminal",                     "Еквайринг",    "POS-термінал"),
    ("/payment-link",                 "Еквайринг",    "Платіжне посилання"),
    ("/acquiring",                    "Еквайринг",    "Еквайринг загальне"),
    ("/beauty",                       "Пакети",       "Краса"),
    ("/events",                       "Пакети",       "Івенти"),
    ("/insta-shops",                  "Пакети",       "Інтернет-магазини"),
    ("/ecomm",                        "Пакети",       "Інтернет-магазини"),
    ("/subscription-services",        "Пакети",       "Підписки"),
    ("/creators",                     "Пакети",       "Криейтори"),
    ("/advance",                      "Аванс",        "Аванс"),
    ("/chast/vendors",                "Частинами",    "Частинами для вендорів"),
    ("/knowledge-base",               "Інформаційні", "База знань"),
    ("/documents",                    "Інформаційні", "Документи"),
    ("/api-docs",                     "Інформаційні", "API документація"),
    ("/business",                     "ЮО",           "Бізнес загальне"),
    # англомовні версії
    ("/en/business/salary",           "ЗП-проект",    "ЗП-проект"),
    ("/en/business/fop",              "ФОП",          "Відкрити ФОП"),
    ("/en/fop",                       "ФОП",          "Відкрити ФОП"),
    ("/en/plata-by-mono",             "Еквайринг",    "Plata by mono (QR)"),
    ("/en/qr-sign",                   "Еквайринг",    "Plata by mono (QR)"),
    ("/en/pos",                       "Еквайринг",    "POS-термінал"),
    ("/en/terminal",                  "Еквайринг",    "POS-термінал"),
    ("/en/payment-link",              "Еквайринг",    "Платіжне посилання"),
    ("/en/acquiring",                 "Еквайринг",    "Еквайринг загальне"),
    ("/en/advance",                   "Аванс",        "Аванс"),
    ("/en/api-docs",                  "Інформаційні", "API документація"),
    ("/en/business",                  "ЮО",           "Бізнес загальне"),
    # кабінетні
    ("/mono-business/actualization",  "Кабінет",      "Актуалізація"),
    ("/mono-business",                "Кабінет",      "Головна кабінету"),
    ("/corp/client",                  "Кабінет",      "Корпоративний кабінет"),
    ("/acquiring-t2p-onboard",        "Еквайринг",    "Онбординг T2P"),
    ("/acquiring-onboard",            "Еквайринг",    "Онбординг еквайрингу"),
    ("/fop/onboarding",               "ФОП",          "Онбординг ФОП"),
    ("/qr",                           "Еквайринг",    "QR-оплата"),
]

BRANDED_KEYWORDS = [
    "mono", "monobank", "монобанк", "монобізнес", "монобиз",
    "monoбізнес", "монопей", "plata", "плата бай моно",
]

ALL_TRACKED_PAGES = BUSINESS_PAGES + CABINET_PAGES


def get_product_by_url(page_path: str) -> tuple[str, str]:
    """Повертає (product, sub_product) для заданого URL."""
    for prefix, product, sub_product in URL_PRODUCT_MAP:
        if page_path.startswith(prefix):
            return product, sub_product
    return "Unknown", "Unknown"


def is_business_page(page_path: str) -> bool:
    return any(page_path.startswith(p) for p in ALL_TRACKED_PAGES)
