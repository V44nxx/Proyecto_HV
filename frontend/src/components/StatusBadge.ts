/**
 * Proyecto HV — Status & Format Badges
 * Renders consistent, accessible state indicators.
 */

export function renderStatusBadge(status: string | null | undefined): string {
  if (!status) return `<span class="badge badge-neutral">DESCONOCIDO</span>`;

  const s = status.toUpperCase();

  switch (s) {
    case "COMPLETED":
      return `<span class="badge badge-success">COMPLETADO</span>`;
    case "REVIEW_REQUIRED":
      return `<span class="badge badge-warning">REVISIÓN REQUERIDA</span>`;
    case "PROCESSING":
    case "EXTRACTING":
    case "OCR_COMPLETED":
      return `<span class="badge badge-info">PROCESANDO</span>`;
    case "UPLOADED":
      return `<span class="badge badge-neutral">SUBIDO</span>`;
    case "FAILED":
      return `<span class="badge badge-danger">FALLIDO</span>`;
    case "ACCEPTED":
      return `<span class="badge badge-success">APROBADO</span>`;
    case "CORRECTED":
      return `<span class="badge badge-info">CORREGIDO</span>`;
    case "REJECTED":
      return `<span class="badge badge-danger">RECHAZADO</span>`;
    case "PENDING":
      return `<span class="badge badge-warning">PENDIENTE</span>`;
    default:
      return `<span class="badge badge-neutral">${s}</span>`;
  }
}

export function renderFormatBadge(format: string | null | undefined): string {
  if (!format) return `<span class="badge badge-neutral">SIN CLASIFICAR</span>`;

  const f = format.toUpperCase();

  switch (f) {
    case "FORMATO_UNICO":
      return `<span class="badge badge-info" title="Formato Único de Hoja de Vida DAFP">FORMATO ÚNICO</span>`;
    case "ATS":
      return `<span class="badge badge-success" title="Formato Libre / ATS">ATS</span>`;
    case "UNKNOWN":
      return `<span class="badge badge-warning" title="Formato desconocido">DESCONOCIDO</span>`;
    default:
      return `<span class="badge badge-neutral">${f}</span>`;
  }
}
