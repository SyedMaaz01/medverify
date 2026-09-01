import { Outlet, NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";
import { api } from "../api";

export function Layout() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + "/");

  useEffect(() => {
    const token = localStorage.getItem("medverify_token");
    if (token) {
      api.getProfile()
        .then((profile) => {
          setIsAdmin(profile.role === "admin" || profile.role === "super_admin");
        })
        .catch(() => {
          setIsAdmin(false);
        });
    }
  }, []);

  return (
    <div className="min-h-screen flex flex-col" dir={i18n.language === "ur" ? "rtl" : "ltr"}>
      <header className="bg-white border-b border-neutral-200 px-4 py-3 shadow-sm">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2 text-neutral-900 font-bold text-xl">
            <svg className="w-8 h-8 text-genuine-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            MedVerify
          </NavLink>

          <nav className="hidden md:flex items-center gap-6">
            <NavLink
              to="/"
              className={`text-sm font-medium transition-colors ${
                isActive("/") ? "text-genuine-600" : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              {t("verify.title")}
            </NavLink>
            <NavLink
              to="/manufacturer"
              className={`text-sm font-medium transition-colors ${
                isActive("/manufacturer") ? "text-genuine-600" : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              {t("mfr.title")}
            </NavLink>
            {isAdmin && (
              <NavLink
                to="/admin"
                className={`text-sm font-medium transition-colors ${
                  isActive("/admin") ? "text-genuine-600" : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                {t("admin.title")}
              </NavLink>
            )}
          </nav>

          <div className="relative">
            <button
              onClick={() => setShowLangMenu(!showLangMenu)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-neutral-700 bg-neutral-100 rounded-full hover:bg-neutral-200"
              aria-label="Change language"
              aria-expanded={showLangMenu}
            >
              <span className="text-lg">🌐</span>
              {i18n.language === "en" ? "EN" : "UR"}
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showLangMenu && (
              <div className="absolute right-0 mt-1 w-32 bg-white border border-neutral-200 rounded-lg shadow-lg py-1 z-10">
                <button
                  onClick={() => {
                    i18n.changeLanguage("en");
                    document.dir = "ltr";
                    setShowLangMenu(false);
                  }}
                  className={`w-full px-4 py-2 text-left text-sm ${
                    i18n.language === "en" ? "bg-genuine-50 text-genuine-700" : "text-neutral-700 hover:bg-neutral-50"
                  }`}
                >
                  {t("lang.english")}
                </button>
                <button
                  onClick={() => {
                    i18n.changeLanguage("ur");
                    document.dir = "rtl";
                    setShowLangMenu(false);
                  }}
                  className={`w-full px-4 py-2 text-left text-sm ${
                    i18n.language === "ur" ? "bg-genuine-50 text-genuine-700" : "text-neutral-700 hover:bg-neutral-50"
                  }`}
                >
                  {t("lang.urdu")}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="bg-neutral-50 border-t border-neutral-200 px-4 py-4">
        <div className="max-w-6xl mx-auto text-center text-sm text-neutral-500">
          MedVerify MVP &copy; 2024 - Medicine Batch Authenticity Verification
        </div>
      </footer>
    </div>
  );
}