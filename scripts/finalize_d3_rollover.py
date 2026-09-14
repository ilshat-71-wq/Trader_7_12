from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]


def between(text, start, end, replacement):
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + replacement + text[b:]


def patch_oi():
    p = ROOT / 'Program/services/open_interest_service.py'
    s = p.read_text()
    s = s.replace('    VERSION = "1.5.0"', '    VERSION = "1.5.1"', 1)
    new_calendar = '''    def _load_expiry_calendar(self, as_of=None):
        """Load exact MOEX expiry metadata over a forward range."""
        if isinstance(as_of, datetime):
            as_of = as_of.date()
        as_of = as_of or date.today()
        key = as_of.isoformat()
        if key in self._expiry_calendar_cache:
            return dict(self._expiry_calendar_cache[key])
        till = as_of + timedelta(days=180)
        url = f"{self.MOEX_FUTURES_CALENDAR_URL}?{urlencode({'from': key, 'till': till.isoformat()})}"
        try:
            payload = self._http_get(url, timeout=self.TIMEOUT)
        except Exception:
            self._expiry_calendar_cache[key] = {}
            return {}
        blocks = []
        sec = payload.get('securities') if isinstance(payload, dict) else None
        if isinstance(sec, dict):
            if isinstance(sec.get('forts'), dict):
                blocks.append(sec['forts'])
            if sec.get('columns') and sec.get('data'):
                blocks.append(sec)
        if isinstance(payload, dict) and isinstance(payload.get('forts'), dict):
            blocks.append(payload['forts'])
        result = {}
        for block in blocks:
            cols = [str(x).lower() for x in block.get('columns', [])]
            rows = [dict(zip(cols, r)) for r in block.get('data', []) if isinstance(r, list)]
            for row in rows:
                raw = str(row.get('expiration_date') or row.get('expirationdate') or row.get('expiration') or '').strip()[:10]
                if not raw:
                    continue
                try:
                    expiry = date.fromisoformat(raw)
                except ValueError:
                    continue
                for key_name in ('secid', 'ticker', 'securityid', 'security_code', 'securitycode', 'symbol'):
                    value = str(row.get(key_name) or '').strip().upper()
                    if value:
                        result[value] = expiry
        self._expiry_calendar_cache[key] = result
        return dict(result)

    def _exact_marketdata_expiry(self, secid, as_of=None):
        return self._load_expiry_calendar(as_of=as_of).get(str(secid or '').strip().upper())

    def _marketdata_candidates(self, rows, as_of=None):
        as_of = as_of or date.today()
        if isinstance(as_of, datetime):
            as_of = as_of.date()
        grouped = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            secid = str(row.get('secid') or row.get('ticker') or '').strip().upper()
            family = self._marketdata_family(secid)
            oi = self._number(row.get('openposition'))
            if not secid or not family or oi <= 0:
                continue
            expiry = self._exact_marketdata_expiry(secid, as_of)
            if expiry is None or expiry < as_of:
                continue
            grouped.setdefault(family, []).append((expiry, secid, row))
        for values in grouped.values():
            values.sort(key=lambda item: (item[0], item[1]))
        return grouped

    def _working_marketdata_rows(self, rows, as_of=None):
        as_of = as_of or date.today()
        if isinstance(as_of, datetime):
            as_of = as_of.date()
        selected = {}
        for family, candidates in self._marketdata_candidates(rows, as_of).items():
            front_expiry, front_secid, _ = candidates[0]
            days = (front_expiry - as_of).days
            if days <= self.ROLLOVER_DAYS_BEFORE_EXPIRY:
                if len(candidates) < 2:
                    continue
                expiry, secid, row = candidates[1]
                role = 'NEXT'
                rollover = True
            else:
                expiry, secid, row = candidates[0]
                role = 'FRONT'
                rollover = False
            item = dict(row)
            item.update({
                '_moex_family': family,
                '_moex_expiry': expiry.isoformat(),
                '_moex_curve_role': role,
                '_moex_working_contract': secid,
                '_moex_front_contract': front_secid,
                '_moex_rollover_active': rollover,
                '_moex_days_to_expiry': days,
            })
            selected[family] = item
        return selected

'''
    s = between(s, '    def _load_expiry_calendar(', '    @classmethod\n    def _marketdata_expiry', new_calendar)
    s = between(s, '    @classmethod\n    def _front_marketdata_rows', '    def marketdata_front_contracts', '''    def _front_marketdata_rows(self, rows, as_of=None):
        return self._working_marketdata_rows(rows, as_of=as_of)

''')
    new_curve = '''    def marketdata_curve_contracts(self, as_of=None):
        as_of = as_of or date.today()
        if isinstance(as_of, datetime):
            as_of = as_of.date()
        result = {}
        for family, candidates in self._marketdata_candidates(self._load_marketdata_all(), as_of).items():
            curve = {}
            for rank, (expiry, secid, row) in enumerate(candidates[:2], 1):
                item = dict(row)
                item.update({'_moex_family': family, '_moex_expiry': expiry.isoformat(), '_moex_curve_rank': rank, '_moex_curve_role': 'FRONT' if rank == 1 else 'NEXT'})
                curve['front' if rank == 1 else 'next'] = item
            if curve:
                result[family] = curve
        return result

'''
    s = between(s, '    def marketdata_curve_contracts(', '    def _request_marketdata_family', new_curve)
    s = between(s, '    def _request_marketdata_family(', '    @staticmethod\n    def _number', '''    def _request_marketdata_family(self, root):
        root = str(root or '').strip().upper()
        if not root:
            return None
        return self._working_marketdata_rows(self._load_marketdata_all(), date.today()).get(root)

''')
    p.write_text(s)


def patch_scanner():
    p = ROOT / 'Program/services/futures_oi_marketdata_scanner_service.py'
    s = p.read_text()
    s = s.replace('self.oi._front_marketdata_rows(resilient_rows, as_of=as_of)', 'self.oi._working_marketdata_rows(resilient_rows, as_of=as_of)')
    s = s.replace('"selection_policy": "MOEX_RFUD_FRONT_NONEXPIRED_NONZERO_OI_PER_FAMILY",', '"selection_policy": "MOEX_RFUD_EXACT_EXPIRY_D3_ROLLOVER_PER_FAMILY",')
    marker = '            "marketdata_error": marketdata_error,\n'
    extra = '''            "moex_expiry_source": "MOEX_FUTURES_CALENDAR_EXACT_ONLY",
            "moex_rollover_rule": "D-3_CALENDAR_DAYS",
            "moex_working_contracts": sum(1 for item in front_contracts.values() if item.get("_moex_working_contract")),
            "moex_rollover_active": sum(1 for item in front_contracts.values() if item.get("_moex_rollover_active")),
'''
    if extra not in s:
        s = s.replace(marker, marker + extra, 1)
    p.write_text(s)


if __name__ == '__main__':
    patch_oi()
    patch_scanner()
    print('D3_FINALIZE_PATCH_APPLIED')
