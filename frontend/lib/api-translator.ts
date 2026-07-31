/**
 * API Content & Category Translation Module for DistillNews.
 *
 * Provides category label & description translations and client-side translation helpers
 * for dynamic news content retrieved from the backend API.
 */

import { LanguageCode } from "./i18n";

export const CATEGORY_TRANSLATIONS: Record<LanguageCode, Record<string, string>> = {
  en: {
    All: "All",
    Technology: "Technology",
    Science: "Science",
    Business: "Business",
    World: "World",
    India: "India",
    Politics: "Politics",
    Health: "Health",
    Entertainment: "Entertainment",
    Sports: "Sports",
    General: "General",
  },
  es: {
    All: "Todos",
    Technology: "Tecnología",
    Science: "Ciencia",
    Business: "Negocios",
    World: "Mundo",
    India: "India",
    Politics: "Política",
    Health: "Salud",
    Entertainment: "Entretenimiento",
    Sports: "Deportes",
    General: "General",
  },
  hi: {
    All: "सभी",
    Technology: "प्रौद्योगिकी",
    Science: "विज्ञान",
    Business: "व्यापार",
    World: "विश्व",
    India: "भारत",
    Politics: "राजनीति",
    Health: "स्वास्थ्य",
    Entertainment: "मनोरंजन",
    Sports: "खेल",
    General: "सामान्य",
  },
  fr: {
    All: "Tous",
    Technology: "Technologie",
    Science: "Science",
    Business: "Économie",
    World: "Monde",
    India: "Inde",
    Politics: "Politique",
    Health: "Santé",
    Entertainment: "Divertissement",
    Sports: "Sports",
    General: "Général",
  },
  de: {
    All: "Alle",
    Technology: "Technologie",
    Science: "Wissenschaft",
    Business: "Wirtschaft",
    World: "Welt",
    India: "Indien",
    Politics: "Politik",
    Health: "Gesundheit",
    Entertainment: "Unterhaltung",
    Sports: "Sport",
    General: "Allgemein",
  },
};

export const CATEGORY_DESCRIPTIONS: Record<LanguageCode, Record<string, string>> = {
  en: {
    Technology: "AI, software, gadgets & tech news",
    Business: "Markets, startups & global economy",
    Science: "Space, physics & environmental research",
    Health: "Medicine, wellness & healthcare",
    Entertainment: "Movies, music & culture",
    Sports: "Athletics, leagues & major tournaments",
    World: "Global affairs & international news",
  },
  es: {
    Technology: "Noticias de IA, software y gadgets",
    Business: "Mercados, startups y economía global",
    Science: "Espacio, física e investigación ambiental",
    Health: "Medicina, bienestar y salud",
    Entertainment: "Cine, música y cultura",
    Sports: "Deportes, ligas y torneos principales",
    World: "Asuntos globales y noticias internacionales",
  },
  hi: {
    Technology: "AI, सॉफ़्टवेयर और तकनीक समाचार",
    Business: "बाज़ार, स्टार्टअप और वैश्विक अर्थव्यवस्था",
    Science: "अंतरिक्ष, भौतिकी और पर्यावरण शोध",
    Health: "चिकित्सा, स्वास्थ्य और कल्याण",
    Entertainment: "फ़िल्में, संगीत और संस्कृति",
    Sports: "खेल, लीग और प्रमुख टूर्नामेंट",
    World: "वैश्विक मामले और अंतर्राष्ट्रीय समाचार",
  },
  fr: {
    Technology: "IA, logiciels, gadgets & actus tech",
    Business: "Marchés, startups & économie mondiale",
    Science: "Espace, physique & recherche",
    Health: "Médecine, bien-être & santé",
    Entertainment: "Films, musique & culture",
    Sports: "Athlétisme, ligues & grands tournois",
    World: "Affaires mondiales & internationales",
  },
  de: {
    Technology: "KI, Software, Gadgets & Tech-News",
    Business: "Märkte, Startups & Weltwirtschaft",
    Science: "Weltraum, Physik & Umweltforschung",
    Health: "Medizin, Wellness & Gesundheit",
    Entertainment: "Filme, Musik & Kultur",
    Sports: "Sport, Ligen & große Turniere",
    World: "Weltgeschehen & Internationale News",
  },
};

/**
 * Translate a category name into the active language.
 */
export function translateCategory(category: string, lang: LanguageCode): string {
  const dict = CATEGORY_TRANSLATIONS[lang] || CATEGORY_TRANSLATIONS.en;
  return dict[category] || category;
}

/**
 * Translate a category description into the active language.
 */
export function translateCategoryDescription(category: string, lang: LanguageCode, defaultDesc?: string): string {
  const dict = CATEGORY_DESCRIPTIONS[lang] || CATEGORY_DESCRIPTIONS.en;
  return dict[category] || defaultDesc || category;
}
