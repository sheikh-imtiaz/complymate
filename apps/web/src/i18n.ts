import { getRequestConfig } from "next-intl/server";

// English first. Add locales by adding messages/<locale>.json and reading the user's preference here.
export default getRequestConfig(async () => {
  const locale = "en";
  return { locale, messages: (await import(`../messages/${locale}.json`)).default };
});
