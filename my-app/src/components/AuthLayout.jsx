import React from 'react';
export default function AuthLayout({ children }) {
  return <main className="auth-shell"><section className="auth-story"><span className="brand-logo">DASH</span><h1>Um olhar claro sobre seus resultados.</h1><p>Reúna os dados dos seus clientes e acompanhe suas campanhas em um só espaço de trabalho.</p><div className="auth-caption">Data. Performance. Clarity.<br />Google Ads · Meta Ads</div></section><section className="dash-panel auth-form-panel"><span className="brand-logo auth-mobile-logo">DASH</span>{children}</section></main>;
}
