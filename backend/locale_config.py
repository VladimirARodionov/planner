from fluent.runtime import FluentLocalization, FluentResourceLoader

loader = FluentResourceLoader("backend/locale_files/{locale}")

i18n = FluentLocalization(["ru"], ["main.ftl"], loader)
