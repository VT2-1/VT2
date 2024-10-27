class View:
    def __init__(self, api, parent, qwclass):
        self.api = api
        self.parent = parent
        self.qwclass = qwclass  # Предположим, что qwclass является уникальным идентификатором

    def __eq__(self, other):
        if not isinstance(other, View):
            return NotImplemented
        # Сравниваем необходимые атрибуты
        return (self.qwclass == other.qwclass)

    def __hash__(self):
        # Важно переопределить __hash__, если вы переопределяете __eq__
        return hash((self.api, self.parent, self.qwclass))

# Пример использования
view = View("api", "self", qwclass="self.tab")

for v in [View("api", "self", qwclass="self.tab")]:
    if v == view:
        print("YEEEEEEEAH")
