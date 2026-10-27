from app import roadmap as rm

ZHIRNYY = """# Карта

- [x] **Этап 0 · Основа.** (закрыт 01.10.2026) текст
  Маркер: сервер отвечает.
- [ ] **Этап 1 · Данные.** текст
  Маркер: импорт прошёл.
- [ ] **Этап 2 · Экран — заморожен до весны.**
"""

ZAGOLOVKI = """# Карта

## Этап 1 · Перенос (закрыт 02.10.2026)
Маркер: всё собирается.

## Этап 2 · Дизайн
Готово, когда: Lighthouse ≥ 95.

## Этап 3 · Деплой
"""

TABLICA = """| № | Этап | Готово, когда | Статус |
|---|---|---|---|
| 1 | Основы | упражнения | готово 01.10 |
| 2 | Владение | список | |
| 3 | Wasm — заморожен | демо | |
"""

PROSTYE = """- [x] Цепь
- [ ] Колодки
- [ ] Гидравлика
"""


def test_zhirnyy():
    e = rm.razobrat_kartu(ZHIRNYY)
    assert [(x.n, x.title, x.done) for x in e] == [(0, "Основа", True), (1, "Данные", False),
                                                   (2, "Экран — заморожен до весны", False)]
    assert e[0].marker == "сервер отвечает."
    assert e[2].zamorozhen


def test_zagolovki():
    e = rm.razobrat_kartu(ZAGOLOVKI)
    assert [(x.n, x.done) for x in e] == [(1, True), (2, False), (3, False)]
    assert e[1].marker == "Lighthouse ≥ 95."
    assert [s for _, s in rm.statusy(e)] == ["done", "cur", "todo"]


def test_tablica():
    e = rm.razobrat_kartu(TABLICA)
    assert [(x.n, x.title, x.done, x.zamorozhen) for x in e] == [
        (1, "Основы", True, False), (2, "Владение", False, False), (3, "Wasm — заморожен", False, True)]


def test_prostye_numeruyutsya_po_poryadku():
    e = rm.razobrat_kartu(PROSTYE)
    assert [(x.n, x.done) for x in e] == [(1, True), (2, False), (3, False)]


def test_progress_bez_zamorozhennyh():
    assert rm.progress(rm.razobrat_kartu(ZHIRNYY)) == 50
    assert rm.progress(rm.razobrat_kartu(TABLICA)) == 50
    assert rm.progress([]) == 0


def test_pustoy_tekst():
    assert rm.razobrat_kartu("") == []
    assert rm.razobrat_kartu("# просто заметка\nбез этапов") == []


def test_pravit_zhirnyy_done_i_obratno():
    text, itog = rm.pravit_kartu(ZHIRNYY, 1, "done", "27.10.2026")
    assert itog == "izmenen"
    assert "- [x] **Этап 1 · Данные.** (закрыт 27.10.2026) текст" in text
    assert rm.razobrat_kartu(text)[1].done
    back, itog = rm.pravit_kartu(text, 1, "todo", "27.10.2026")
    assert itog == "izmenen" and back == ZHIRNYY


def test_pravit_povtorno_bez_izmeneniy():
    text, _ = rm.pravit_kartu(ZHIRNYY, 1, "done", "27.10.2026")
    again, itog = rm.pravit_kartu(text, 1, "done", "28.10.2026")
    assert itog == "bez_izmeneniy" and again == text


def test_pravit_zagolovok():
    text, itog = rm.pravit_kartu(ZAGOLOVKI, 2, "done", "27.10.2026")
    assert itog == "izmenen"
    assert "## Этап 2 · Дизайн (закрыт 27.10.2026)" in text


def test_pravit_tablicu_v_kolonke_statusa():
    text, itog = rm.pravit_kartu(TABLICA, 2, "done", "27.10.2026")
    assert itog == "izmenen"
    assert "| 2 | Владение | список | готово 27.10 |" in text
    assert rm.razobrat_kartu(text)[1].done


def test_pravit_prostoy():
    text, itog = rm.pravit_kartu(PROSTYE, 2, "done", "27.10.2026")
    assert "- [x] Колодки (закрыт 27.10.2026)" in text and itog == "izmenen"


def test_net_etapa():
    assert rm.pravit_kartu(ZHIRNYY, 9, "done", "27.10.2026")[1] == "ne_nayden"


def test_crlf_sohranyaetsya():
    crlf = PROSTYE.replace("\n", "\r\n")
    text, _ = rm.pravit_kartu(crlf, 3, "done", "27.10.2026")
    assert text.count("\r\n") == crlf.count("\r\n")


def test_data_zakrytiya():
    assert rm.data_zakrytiya("- [x] **Этап 0 · Основа.** (закрыт 01.10.2026)").date().isoformat() == "2026-10-01"
    assert rm.data_zakrytiya("| 1 | Основы | x | готово 01.10 |", god=2026).date().isoformat() == "2026-10-01"
    assert rm.data_zakrytiya("- [ ] **Этап 1 · Данные.**") is None
