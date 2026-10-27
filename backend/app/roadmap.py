"""Разбор дорожной карты проекта — чистые функции над строками, без базы и файловой системы.

Файл карты лежит в папке проекта (рядом со спецификацией и журналом) и остаётся источником правды;
сервер хранит разобранный кэш этапов. Поддерживаются формы, в которых карты пишутся на практике:

1. чекбокс с жирным заголовком:
       - [x] **Этап 0 · Спецификация и среда.** (закрыт 21.09.2026) текст…
         Маркер: что показывает, что этап закрыт.
2. заголовок `## Этап N · Название` (или `## Этап N. Название`), под ним текст и «Маркер: …»;
   закрыт — если в заголовке или первой строке есть «(закрыт …)» / «[x]» / «✓»;
3. таблица `| № | Этап | … | Готово, когда | Статус |` (razobrat_tablicu);
4. простые чекбоксы `- [ ] текст` / `- [x] текст` — нумеруются по порядку.
Этап с пометкой « — заморожен» в названии не входит в прогресс.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
_RE_CHECKBOX = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$")
_RE_ETAP_ZHIRNYY = re.compile(r"^\*\*Этап\s+(\d+)\s*[·.:—-]?\s*(.+?)\*\*\s*(.*)$", re.S)
# «## Этап 1. …», «## Э0. …», «## Пакет 2 · …»
_RE_ETAP_ZAGOLOVOK = re.compile(r"^#{2,4}\s+(?:Этап\s+|Э|Пакет\s+)(\d+)\s*[·.:—-]?\s*(.*?)\s*$")
# «Маркер: …», «**Маркер:** …», «**Готово, когда:** …», «Признак готовности: …»
_RE_MARKER = re.compile(r"^\s*(?:[-*]\s+)?\**\s*(?:Маркер(?:\s+готовности)?|Готово,?\s+когда|Признак\s+готовности)"
                        r"\s*\**\s*[:：]\s*\**\s*(.*)$", re.I)
_RE_ZAKRYT = re.compile(r"\((закрыт|закрыто|готово|сделано)[^)]*\)|\[x\]|✓|✔|✅"
                        r"|[—–-]\s*(?:закрыт|закрыто|готово|сделано|принят)(?![а-яё])(?:\s+\d{1,2}\.\d{1,2}(?:\.\d{4})?)?", re.I)
_RE_TABL = re.compile(r"^\s*\|.*\|\s*$")
_RE_TABL_RAZDEL = re.compile(r"^\s*\|?(\s*:?-{2,}:?\s*\|)+\s*:?-*:?\s*\|?\s*$")
_RE_TABL_NOMER = re.compile(r"^\s*(\d+)([а-яёa-z]?)(?![\d.,]\d)\s*[.)·:—–-]?\s*(.*)$", re.I | re.S)
_RE_GALKA = re.compile(r"✅|✓|✔|☑|\[x\]", re.I)
_RE_GOTOVO_STATUS = re.compile(r"^\W*(?:готово|готов|сделано|закрыт\w*|принят\w*|done)(?![а-яё])", re.I)
_RE_GOTOVO_HVOST = re.compile(r"\s*[—–-]\s*(?:принят|закрыт|готов|сделан)\w*(?:\s+\d{1,2}\.\d{1,2}(?:\.\d{4})?)?\s*$", re.I)
_RE_ZAMOROZHEN = re.compile(r"(?:^|\s)[—–-]\s*заморожен(?![а-яё])", re.I)
_RE_GALKA_DATA = re.compile(r"(?:✅|✓|✔|☑)\s*(?:\d{1,2}\.\d{1,2}(?:\.\d{4})?)?")


@dataclass
class EtapIzFayla:
    n: int
    title: str
    marker: Optional[str]
    done: bool
    line_no: int
    forma: str = ""                     # zhirnyy | zagolovok | prostoy | tablica
    zamorozhen: bool = False            # «— заморожен …» в названии: вне прогресса и автозакрытия


def _chistit(s: str) -> str:
    s = s.strip().strip("*").strip()
    return s[:-1] if s.endswith(".") else s


def _dobavit(spisok: list[EtapIzFayla], e: EtapIzFayla, hvost: list[str]) -> None:
    """Дописать хвост (строки под этапом) в маркер, если он ещё не найден."""
    if e.marker is None:
        for stroka in hvost:
            m = _RE_MARKER.match(stroka)
            if m:
                e.marker = m.group(1).strip().strip("* ") or None
                break
    spisok.append(e)


def _yacheyki(stroka: str) -> list[str]:
    return [c.strip() for c in stroka.strip().strip("|").split("|")]


def _vid_kolonki(zagolovok: str) -> Optional[str]:
    z = zagolovok.strip().strip("*").strip().lower()
    if z in ("№", "#", "n", "no", "номер"):
        return "nomer"
    if z.startswith(("этап", "пакет")):
        return "etap"
    if "готово" in z and "когда" in z or z.startswith(("маркер", "признак", "готовность")):
        return "marker"
    if z.startswith("статус"):
        return "status"
    return None


def razobrat_tablicu(stroki: list[str]) -> list[EtapIzFayla]:
    """Карта-таблица `| № | Этап | … | Готово, когда |`: первая таблица, где есть колонка номера или этапа
    и колонка маркера или статуса. Закрыт — ✅/✓ в ячейке номера/этапа, «готово/принят/закрыт» в «Статусе»
    или «— принят …» в названии. Номера не все целые или повторяются (2а, 2б, строки без номера) — по порядку."""
    i = 0
    while i < len(stroki) - 1:
        if not (_RE_TABL.match(stroki[i]) and _RE_TABL_RAZDEL.match(stroki[i + 1])):
            i += 1
            continue
        vidy = [_vid_kolonki(z) for z in _yacheyki(stroki[i])]
        k_nomer = vidy.index("nomer") if "nomer" in vidy else None
        k_etap = vidy.index("etap") if "etap" in vidy else None
        k_marker = vidy.index("marker") if "marker" in vidy else None
        k_status = vidy.index("status") if "status" in vidy else None
        if (k_nomer is None and k_etap is None) or (k_marker is None and k_status is None):
            i += 2
            while i < len(stroki) and _RE_TABL.match(stroki[i]):
                i += 1
            continue
        k_klyuch = k_nomer if k_nomer is not None else k_etap
        sluzhebnye = {k_klyuch, k_marker, k_status}
        k_title = k_etap if k_etap is not None and k_etap != k_klyuch else next(
            (k for k in range(len(vidy)) if k not in sluzhebnye and k > k_klyuch), None)
        syrye: list[tuple[Optional[int], str, EtapIzFayla]] = []
        j = i + 2
        while j < len(stroki) and _RE_TABL.match(stroki[j]):
            ya = _yacheyki(stroki[j])
            j += 1
            vzyat = lambda k: ya[k] if k is not None and k < len(ya) else ""   # noqa: E731
            klyuch = vzyat(k_klyuch).replace("**", "").strip()
            if not klyuch and not vzyat(k_title):
                continue
            m = _RE_TABL_NOMER.match(klyuch)
            nomer = int(m.group(1)) if m and not m.group(2) else None
            ostatok = (m.group(3) if m else klyuch).strip()
            title_yach = vzyat(k_title).replace("**", "").strip()
            status_yach = vzyat(k_status).replace("**", "").strip()
            done = bool(_RE_GALKA.search(klyuch) or _RE_GALKA.search(title_yach)
                        or _RE_GOTOVO_STATUS.match(status_yach)
                        or _RE_GOTOVO_HVOST.search(ostatok) or _RE_GOTOVO_HVOST.search(title_yach))
            if k_klyuch == k_etap and _RE_GALKA_DATA.sub("", ostatok).strip():
                title = ostatok                   # «0. Сбор», «1. Основа — принят 23.09»
            else:
                title = title_yach or ostatok
            title = _RE_GOTOVO_HVOST.sub("", _RE_GALKA_DATA.sub("", title))
            polnyy = _RE_GOTOVO_HVOST.sub("", _RE_GALKA_DATA.sub("", klyuch if k_klyuch == k_etap else title))
            marker = vzyat(k_marker).replace("**", "").strip() or None
            e = EtapIzFayla(n=0, title=_chistit(title) or _chistit(polnyy), marker=marker, done=done,
                            line_no=j, forma="tablica",
                            zamorozhen=bool(_RE_ZAMOROZHEN.search(" " + klyuch) or _RE_ZAMOROZHEN.search(" " + title_yach)))
            syrye.append((nomer, _chistit(polnyy), e))
        if not syrye:
            return []
        nomera = [n for n, _, _ in syrye]
        po_nomeram = all(n is not None for n in nomera) and len(set(nomera)) == len(nomera)
        for k, (nomer, polnyy, e) in enumerate(syrye, start=1):
            if po_nomeram:
                e.n = nomer
            else:
                e.n = k
                if k_klyuch == k_etap and polnyy:
                    e.title = polnyy              # «2а. Тип письма»: метку не теряем
        return [e for _, _, e in syrye]
    return []


def pravit_stroku_tablicy(stroki: list[str], line_no: int, status: str, data: str) -> Optional[str]:
    """Строка таблицы-карты с этапом в line_no (1-based) после отметки done/todo — для MCP proekt_etap.
    Есть колонка «Статус» — в ней «готово ДД.ММ» или пусто; нет — «✅ ДД.ММ» в ячейке номера/этапа.
    None — строка не из распознанной таблицы."""
    i = line_no - 1
    if not (0 <= i < len(stroki)) or not _RE_TABL.match(stroki[i]):
        return None
    k = i
    while k > 0 and not _RE_TABL_RAZDEL.match(stroki[k]):
        k -= 1
    if k < 1 or not _RE_TABL.match(stroki[k - 1]):
        return None
    vidy = [_vid_kolonki(z) for z in _yacheyki(stroki[k - 1])]
    ya = _yacheyki(stroki[i])
    dm = data[:5]
    if "status" in vidy and vidy.index("status") < len(ya):
        ks = vidy.index("status")
        ya[ks] = f"готово {dm}" if status == "done" else ""
    else:
        kk = vidy.index("nomer") if "nomer" in vidy else vidy.index("etap") if "etap" in vidy else None
        if kk is None or kk >= len(ya):
            return None
        chisto = _RE_GOTOVO_HVOST.sub("", _RE_GALKA_DATA.sub("", ya[kk])).strip()
        ya[kk] = f"{chisto} ✅ {dm}" if status == "done" else chisto
    otstup = stroki[i][:len(stroki[i]) - len(stroki[i].lstrip())]
    return otstup + "| " + " | ".join(ya) + " |"


def razobrat_kartu(text: str) -> list[EtapIzFayla]:
    """Этапы из текста дорожной карты. Пустой список — карты в тексте не нашли."""
    if not text:
        return []
    stroki = text.splitlines()
    etapy: list[EtapIzFayla] = []
    tekushchiy: Optional[EtapIzFayla] = None
    hvost: list[str] = []
    prostye: list[EtapIzFayla] = []

    def zakryt_tekushchiy():
        nonlocal tekushchiy, hvost
        if tekushchiy is not None:
            _dobavit(etapy, tekushchiy, hvost)
        tekushchiy, hvost = None, []

    for i, stroka in enumerate(stroki, start=1):
        m_cb = _RE_CHECKBOX.match(stroka)
        if m_cb:
            done = m_cb.group(1).lower() == "x"
            telo = m_cb.group(2).strip()
            m_zh = _RE_ETAP_ZHIRNYY.match(telo)
            zakryt_tekushchiy()
            if m_zh:
                tekushchiy = EtapIzFayla(n=int(m_zh.group(1)), title=_chistit(m_zh.group(2)),
                                         marker=None, done=done, line_no=i, forma="zhirnyy",
                                         zamorozhen=bool(_RE_ZAMOROZHEN.search(" " + telo)))
                # маркер может стоять в той же строке после заголовка
                m_mk = _RE_MARKER.search(m_zh.group(3) or "")
                if m_mk:
                    tekushchiy.marker = m_mk.group(1).strip().strip("* ") or None
            else:
                prostye.append(EtapIzFayla(n=0, title=_chistit(telo), marker=None, done=done, line_no=i,
                                           forma="prostoy", zamorozhen=bool(_RE_ZAMOROZHEN.search(" " + telo))))
            continue
        m_zg = _RE_ETAP_ZAGOLOVOK.match(stroka)
        if m_zg:
            zakryt_tekushchiy()
            title_raw = m_zg.group(2)
            tekushchiy = EtapIzFayla(n=int(m_zg.group(1)), title=_chistit(_RE_ZAKRYT.sub("", title_raw)),
                                     marker=None, done=bool(_RE_ZAKRYT.search(title_raw)), line_no=i,
                                     forma="zagolovok", zamorozhen=bool(_RE_ZAMOROZHEN.search(" " + title_raw)))
            continue
        if tekushchiy is not None:
            if stroka.startswith("#"):
                zakryt_tekushchiy()
                continue
            if not hvost and not tekushchiy.done and _RE_ZAKRYT.search(stroka):
                tekushchiy.done = True
            hvost.append(stroka)
    zakryt_tekushchiy()

    if etapy:
        etapy.sort(key=lambda e: e.n)
        return etapy
    tablica = razobrat_tablicu(stroki)
    if tablica:
        return tablica
    for k, e in enumerate(prostye, start=1):
        e.n = k
    return prostye


def statusy(etapy: list[EtapIzFayla]) -> list[tuple[EtapIzFayla, str]]:
    """(этап, status) — done по файлу, cur — первый незакрытый, остальные todo."""
    out: list[tuple[EtapIzFayla, str]] = []
    cur_naiden = False
    for e in etapy:
        if e.done:
            out.append((e, "done"))
        elif not cur_naiden:
            out.append((e, "cur"))
            cur_naiden = True
        else:
            out.append((e, "todo"))
    return out





_RE_DATA_ZAKRYT = re.compile(r"\((?:закрыт|закрыто|готово|сделано)[^)]*?(\d{1,2})\.(\d{1,2})\.(\d{4})", re.I)
# таблицы и заголовки: «0 ✅ 24.09», «готово 01.09», «— принят 23.09», «— ЗАКРЫТ 24.09.2026»
_RE_DATA_ZAKRYT_2 = re.compile(r"(?:✅|✓|✔|☑|готово|принят\w*|закрыт\w*)\s*(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", re.I)


def data_zakrytiya(stroka: str, god: Optional[int] = None) -> Optional[datetime]:
    """«(закрыт 21.09.2026)» в строке этапа → дата; «✅ 24.09» / «готово 01.09» — год из god, иначе
    ближайший, при котором дата не в будущем: «✅ 24.12» в январе — прошлый декабрь."""
    m = _RE_DATA_ZAKRYT.search(stroka or "") or _RE_DATA_ZAKRYT_2.search(stroka or "")
    if not m:
        return None
    try:
        if m.group(3) or god:
            return datetime(int(m.group(3) or god), int(m.group(2)), int(m.group(1)))
        now = datetime.now()
        d = datetime(now.year, int(m.group(2)), int(m.group(1)))
        return d if d <= now else datetime(now.year - 1, int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def progress(etapy: list[EtapIzFayla]) -> int:
    """Процент закрытых этапов без замороженных."""
    zhivye = [e for e in etapy if not e.zamorozhen]
    if not zhivye:
        return 0
    return round(100 * sum(e.done for e in zhivye) / len(zhivye))


# ── правка карты: отметить этап done/todo прямо в тексте файла (форма записи сохраняется) ──

# --- правка файла дорожной карты (те же формы, что у сервера в crm/app/v2/proekty_fayly.py)
_RE_K_CHECKBOX = re.compile(r"^(\s*[-*]\s+\[)( |x|X)(\]\s+)(.*)$")
_RE_K_ZHIRNYY = re.compile(r"^(\*\*Этап\s+(\d+)\b.*?\*\*)(.*)$")
_RE_K_ZAGOLOVOK = re.compile(r"^(#{2,4}\s+(?:Этап\s+|Э|Пакет\s+)(\d+)\b.*?)\s*$")
_RE_K_ZAKRYT = re.compile(r"\s*\((?:закрыт|закрыто|готово|сделано)[^)]*\)", re.I)
# «## Этап 1. … — ЗАКРЫТ 24.09.2026»
_RE_K_ZAKRYT_TIRE = re.compile(r"\s*[—–-]\s*(?:закрыт|закрыто|готово|сделано|принят)(?![а-яё])"
                               r"(?:\s+\d{1,2}\.\d{1,2}(?:\.\d{4})?)?", re.I)


def _dopisat_zakryt(golova: str, hvost: str, data: str) -> str:
    """«**Этап N · …**» + « (закрыт ДД.ММ.ГГГГ)» + остаток, если пометки ещё нет."""
    if _RE_K_ZAKRYT.match(hvost):
        return golova + hvost
    return f"{golova} (закрыт {data})" + (hvost if hvost.startswith((" ", "\t")) or not hvost else " " + hvost)


def _snyat_zakryt(golova: str, hvost: str) -> str:
    return golova + _RE_K_ZAKRYT.sub("", hvost, count=1) if _RE_K_ZAKRYT.match(hvost) else golova + hvost


def pravit_kartu(text: str, n: int, status: str, data: str) -> tuple[str, str]:
    """Новый текст карты и итог: izmenen | bez_izmeneniy | ne_nayden.
    done → «- [x]» и «(закрыт дата)» после жирного заголовка; todo → «- [ ]» и без пометки; cur — как есть."""
    if status == "cur":
        return text, "bez_izmeneniy"
    stroki = text.splitlines(keepends=True)
    cel = None                       # (индекс, форма)
    prostye: list[int] = []
    numerovannye = False
    for i, s in enumerate(stroki):
        telo = s.rstrip("\r\n")
        m_cb = _RE_K_CHECKBOX.match(telo)
        if m_cb:
            m_zh = _RE_K_ZHIRNYY.match(m_cb.group(4))
            if m_zh:
                numerovannye = True
                if int(m_zh.group(2)) == n and cel is None:
                    cel = (i, "zhirnyy")
            else:
                prostye.append(i)
            continue
        m_zg = _RE_K_ZAGOLOVOK.match(telo)
        if m_zg:
            numerovannye = True
            if int(m_zg.group(2)) == n and cel is None:
                cel = (i, "zagolovok")
    if cel is None and not numerovannye:
        etap = next((e for e in razobrat_kartu(text) if e.n == n and e.forma == "tablica"), None)
        if etap is not None:
            stroki_bez = [s.rstrip("\r\n") for s in stroki]
            novaya = pravit_stroku_tablicy(stroki_bez, etap.line_no, status, data)
            if novaya is None:
                return text, "ne_nayden"
            s = stroki[etap.line_no - 1]
            stroki[etap.line_no - 1] = novaya + s[len(s.rstrip("\r\n")):]
            novyy = "".join(stroki)
            return novyy, ("izmenen" if novyy != text else "bez_izmeneniy")
    if cel is None and not numerovannye and 1 <= n <= len(prostye):
        cel = (prostye[n - 1], "prostoy")
    if cel is None:
        return text, "ne_nayden"

    i, forma = cel
    stroka = stroki[i]
    konec = stroka[len(stroka.rstrip("\r\n")):]
    telo = stroka.rstrip("\r\n")
    galka = "x" if status == "done" else " "
    if forma == "zagolovok":
        golova = _RE_K_ZAGOLOVOK.match(telo).group(1)
        if status == "done":
            novaya = golova if _RE_K_ZAKRYT.search(golova) or _RE_K_ZAKRYT_TIRE.search(golova) \
                else f"{golova} (закрыт {data})"
        else:
            novaya = _RE_K_ZAKRYT_TIRE.sub("", _RE_K_ZAKRYT.sub("", golova)).rstrip()
        stroki[i] = novaya + konec
        # у формы с заголовком пометка может стоять первой строкой под ним — при todo снимаем и её
        if status == "todo" and i + 1 < len(stroki) and _RE_K_ZAKRYT.search(stroki[i + 1]):
            stroki[i + 1] = _RE_K_ZAKRYT.sub("", stroki[i + 1], count=1)
    else:
        m_cb = _RE_K_CHECKBOX.match(telo)
        ostatok = m_cb.group(4)
        if forma == "zhirnyy":
            m_zh = _RE_K_ZHIRNYY.match(ostatok)
            golova, hvost = m_zh.group(1), m_zh.group(3)
            ostatok = _dopisat_zakryt(golova, hvost, data) if status == "done" else _snyat_zakryt(golova, hvost)
        else:
            ostatok = _RE_K_ZAKRYT.sub("", ostatok).rstrip()
            if status == "done":
                ostatok = f"{ostatok} (закрыт {data})"
        stroki[i] = m_cb.group(1) + galka + m_cb.group(3) + ostatok + konec
    novyy = "".join(stroki)
    return novyy, ("izmenen" if novyy != text else "bez_izmeneniy")
