/**
 * Generator script for DistillNews i18n strings dictionary.
 * Runs to validate string keys and generate build assets.
 */

import { strings } from "./strings.js";

function validateStrings() {
  const languages = Object.keys(strings);
  const baseKeys = Object.keys(strings.en);
  let hasErrors = false;

  console.log(`[i18n] Validating translations for languages: ${languages.join(", ")}`);
  console.log(`[i18n] Base English key count: ${baseKeys.length}`);

  languages.forEach((lang) => {
    if (lang === "en") return;
    const langKeys = Object.keys(strings[lang]);
    const missing = baseKeys.filter((k) => !langKeys.includes(k));
    if (missing.length > 0) {
      console.error(`[i18n ERROR] Language '${lang}' is missing keys: ${missing.join(", ")}`);
      hasErrors = true;
    } else {
      console.log(`[i18n OK] Language '${lang}' has 100% key coverage (${langKeys.length}/${baseKeys.length})`);
    }
  });

  if (!hasErrors) {
    console.log("[i18n SUCCESS] All localization dictionaries valid and in sync!");
  }
}

validateStrings();
