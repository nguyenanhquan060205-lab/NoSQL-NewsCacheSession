export function getApiStatus(error) {
  return error?.response?.status ?? null;
}

export function getApiMessage(error, fallback = 'Có lỗi xảy ra. Vui lòng thử lại.') {
  const payload = error?.response?.data;

  if (typeof payload?.message === 'string' && payload.message.trim()) {
    return payload.message.trim();
  }

  if (payload?.errors && typeof payload.errors === 'object') {
    const validationMessages = Object.values(payload.errors)
      .flatMap((messages) => (Array.isArray(messages) ? messages : [messages]))
      .filter((message) => typeof message === 'string' && message.trim());

    if (validationMessages.length > 0) return validationMessages.join(' ');
  }

  if (typeof payload?.title === 'string' && payload.title.trim()) {
    return payload.title.trim();
  }

  return fallback;
}

export function getValidationErrors(error) {
  const errors = error?.response?.data?.errors;
  if (!errors || typeof errors !== 'object') return {};

  return Object.entries(errors).reduce((result, [field, messages]) => {
    const message = Array.isArray(messages) ? messages[0] : messages;
    const normalizedField = field.charAt(0).toLowerCase() + field.slice(1);
    if (typeof message === 'string') result[normalizedField] = message;
    return result;
  }, {});
}
