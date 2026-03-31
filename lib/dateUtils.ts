/**
 * Utilitários de data/hora sempre em America/Sao_Paulo (UTC-3).
 * Usa en-CA locale pois é YYYY-MM-DD (confiável em todos os ambientes).
 *
 * IMPORTANTE: Supabase retorna timestamps SEM sufixo Z (ex: "2026-03-30T22:27:49").
 * Sem o Z, new Date() interpreta como horário local do navegador, causando offset.
 * A função toUTC() garante que timestamps sem TZ sejam tratados como UTC.
 */

const TZ = 'America/Sao_Paulo';

/** Garante que timestamps sem timezone info sejam interpretados como UTC */
function toUTC(date: Date | string): Date {
  if (date instanceof Date) return date;
  const s = String(date);
  // Se já tem Z, +XX:XX ou -XX:XX, está ok
  if (/Z|[+-]\d{2}:\d{2}$/.test(s)) return new Date(s);
  // Sem timezone → adicionar Z para interpretar como UTC
  return new Date(s + 'Z');
}

/** Formata hora:minuto no fuso BRT — "14:32" */
export function formatTime(date: Date | string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: TZ,
  }).format(toUTC(date));
}

/** Retorna "YYYY-MM-DD" no fuso BRT para agrupar por dia */
export function toLocalDateKey(date: Date | string): string {
  // en-CA sempre retorna YYYY-MM-DD — confiável em qualquer ambiente
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(
    toUTC(date)
  );
}

/** Subtrai N dias inteiros de uma data em BRT */
function addDaysBRT(offsetDays: number): string {
  // Pegamos a data BRT de hoje e subtraímos dias via UTC para evitar DST
  const nowBRT = new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(
    new Date()
  );
  const [y, m, d] = nowBRT.split('-').map(Number);
  const base = new Date(Date.UTC(y, m - 1, d + offsetDays, 12, 0, 0));
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(base);
}

/** Rótulo do separador de dia estilo WhatsApp */
export function getDaySeparatorLabel(dateKey: string): string {
  const todayKey = addDaysBRT(0);
  const yesterdayKey = addDaysBRT(-1);

  if (dateKey === todayKey) return 'Hoje';
  if (dateKey === yesterdayKey) return 'Ontem';

  const [year, month, day] = dateKey.split('-').map(Number);
  const d = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  const todayYear = Number(todayKey.split('-')[0]);

  if (year === todayYear) {
    return new Intl.DateTimeFormat('pt-BR', {
      day: 'numeric',
      month: 'long',
      timeZone: 'UTC',
    }).format(d);
  }

  return new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(d);
}

/** Tempo relativo compacto para a lista: "agora" / "5 min" / "14:32" / "ontem" / "27/03" */
export function formatRelativeShort(date: Date | string): string {
  const d = toUTC(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'agora';
  if (diffMin < 60) return `${diffMin} min`;

  const todayKey = addDaysBRT(0);
  const yesterdayKey = addDaysBRT(-1);
  const msgKey = toLocalDateKey(d);

  if (msgKey === todayKey) return formatTime(date);
  if (msgKey === yesterdayKey) return 'ontem';

  // Mais de 2 dias: DD/MM
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    timeZone: TZ,
  }).format(toUTC(date));
}
