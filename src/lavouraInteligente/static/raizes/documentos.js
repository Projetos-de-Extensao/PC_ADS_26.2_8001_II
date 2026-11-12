/* Máscara compartilhada pelo portal e pelo Admin. A API armazena o valor canônico. */
'use strict';
window.RaizesDocumento = (() => {
  const clean = value => String(value).toUpperCase().replace(/[. /-]/g, '');
  function mask(value) {
    if (value === 'DEMO-RAIZES') return value;
    const raw = clean(value).replace(/[^A-Z0-9]/g, '').slice(0,14);
    const cpf = !/[A-Z]/.test(raw) && raw.length <= 11;
    const sizes = cpf ? [3,3,3,2] : [2,3,3,4,2];
    const separators = cpf ? ['.','.','-'] : ['.','.','/','-'];
    let cursor = 0, output = '';
    sizes.forEach((size,index) => {
      const part = raw.slice(cursor,cursor+size); cursor += size;
      if (part) output += (index ? separators[index-1] : '') + part;
    });
    return output;
  }
  function valid(value) {
    const raw = clean(value);
    if (!/^(?:[0-9]{11}|[A-Z0-9]{12}[0-9]{2})$/.test(raw) || new Set(raw).size === 1) return false;
    let base = raw.slice(0,-2);
    for (let step=0;step<2;step++) {
      const weights = raw.length === 11 ? Array.from({length:base.length},(_,i)=>base.length+1-i) :
        step === 0 ? [5,4,3,2,9,8,7,6,5,4,3,2] : [6,5,4,3,2,9,8,7,6,5,4,3,2];
      const rest = [...base].reduce((sum,c,i)=>sum+(c.charCodeAt(0)-48)*weights[i],0)%11;
      base += String(rest<2?0:11-rest);
    }
    return base === raw;
  }
  function apply(input) {
    if (input.disabled || input.readOnly) return;
    const before = input.value, at = input.selectionStart ?? before.length;
    const position = before.slice(0,at).replace(/[^A-Za-z0-9]/g,'').length;
    input.value = mask(before);
    let caret=0,count=0;
    while (caret<input.value.length && count<position) {
      if (/[A-Z0-9]/.test(input.value[caret])) count++;
      caret++;
    }
    input.setSelectionRange(caret,caret);
    input.setCustomValidity(!input.value || valid(input.value) ? '' : 'Confira o CPF/CNPJ e os dígitos verificadores.');
  }
  document.addEventListener('input', event => {
    if (event.target.matches('input[data-documento]')) apply(event.target);
  });
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[data-documento]').forEach(input => {
      input.value = mask(input.value);
    });
  });
  return {clean,mask,valid,apply};
})();
