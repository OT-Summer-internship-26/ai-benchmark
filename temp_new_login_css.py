# NOUVELLE VERSION - À copier dans app.py
# Remplacer la fonction _inject_login_css() existante par cette version

def _inject_login_css() -> None:
    """CSS pour page de login PLEIN ÉCRAN."""
    # Charger les logos TRANSPARENTS depuis assets (PAS de LOGO_B64)
    from src.dashboard.login_assets import get_wordmark_white_base64, get_emblem_base64
    
    wordmark_b64 = get_wordmark_white_base64()
    emblem_b64 = get_emblem_base64()
    
    st.markdown(
        f"""
        <style>
        /* Masquer header/footer/sidebar */
        header {{visibility:hidden;}}
        #MainMenu {{visibility:hidden;}}
        footer {{visibility:hidden;}}
        section[data-testid="stSidebar"] {{ display: none !important; }}

        /* Fond plein écran - BLANC (même couleur que la carte) */
        div[data-testid="stAppViewContainer"] {{
            background: #FFFFFF;
            background-attachment: fixed;
        }}
        
        div[data-testid="stMain"] {{ 
            display: flex; 
        }}
        
        /* Container PLEIN ÉCRAN - padding 0 */
        div.block-container {{
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }}

        /* Carte login PLEIN ÉCRAN 100vw x 100vh */
        .st-key-login_card {{
            width: 100vw;
            min-height: 100vh;
            margin: 0;
            background: white;
            border-radius: 0;
            box-shadow: none;
            overflow: hidden;
            display: flex;
        }}
        
        /* Gap 0 entre les colonnes */
        .st-key-login_card > div[data-testid="column"] {{
            padding: 0 !important;
            gap: 0 !important;
        }}
        
        .st-key-login_card > div {{
            gap: 0 !important;
        }}
        
        /* Panneau GAUCHE - Branding Ooredoo PLEIN ÉCRAN */
        .st-key-login_left {{
            background: linear-gradient(165deg, #ED1C24 0%, #B30006 100%);
            padding: 80px 60px;
            position: relative;
            overflow: hidden;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}
        
        /* Bulles décoratives - grande sphère blanche top-right */
        .st-key-login_left::before {{
            content: "";
            position: absolute;
            width: 420px;
            height: 420px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.20) 0%, rgba(255,255,255,0.08) 50%, transparent 75%);
            top: -180px;
            right: -150px;
            pointer-events: none;
            z-index: 1;
        }}
        
        /* Bulle rouge foncé bottom-left */
        .st-key-login_left::after {{
            content: "";
            position: absolute;
            width: 350px;
            height: 350px;
            border-radius: 50%;
            background: radial-gradient(circle at 40% 40%, rgba(179,0,6,0.6) 0%, rgba(139,0,5,0.4) 60%, transparent 80%);
            bottom: -120px;
            left: -100px;
            pointer-events: none;
            z-index: 1;
        }}
        
        /* Contenu du panneau gauche */
        .login-left-content {{
            position: relative;
            z-index: 2;
            text-align: center;
            max-width: 500px;
        }}
        
        /* Wordmark blanc TRANSPARENT - AUCUN FILTRE CSS */
        .login-left-content .wordmark {{
            width: 280px;
            height: auto;
            margin-bottom: 50px;
            display: block;
            margin-left: auto;
            margin-right: auto;
            background: transparent !important;
            box-shadow: none !important;
            border: none !important;
            padding: 0 !important;
        }}
        
        /* Titre principal */
        .login-left-content .brand-title {{
            color: white;
            font-size: 44px;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 24px;
            letter-spacing: -0.5px;
        }}
        
        /* Sous-titre */
        .login-left-content .brand-subtitle {{
            color: rgba(255,255,255,0.90);
            font-size: 18px;
            line-height: 1.6;
            font-weight: 400;
        }}
        
        /* Bulle avec emblème (sphère blanche en bas) */
        .emblem-bubble {{
            position: absolute;
            bottom: 60px;
            right: 60px;
            width: 170px;
            height: 170px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.12) 60%, transparent 85%);
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            z-index: 1;
        }}
        
        .emblem-bubble img {{
            width: 80px;
            height: auto;
            opacity: 0.85;
        }}
        
        /* Panneau DROIT - Formulaire PLEIN ÉCRAN */
        .st-key-login_right {{
            padding: 80px 60px;
            background: #FFFFFF;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}
        
        /* Conteneur du formulaire */
        .login-form-container {{
            max-width: 420px;
            width: 100%;
        }}
        
        .st-key-login_right h2 {{
            color: #1a1a1a;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .st-key-login_right .form-subtitle {{
            color: #6B7280;
            font-size: 15px;
            margin-bottom: 36px;
        }}
        
        /* Inputs du formulaire */
        .st-key-login_right input {{
            background: #F3F4F7 !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            font-size: 15px !important;
            transition: all 0.2s ease;
        }}
        
        .st-key-login_right input:focus {{
            border-color: #ED1C24 !important;
            box-shadow: 0 0 0 3px rgba(237,28,36,0.08) !important;
            background: #FFFFFF !important;
        }}
        
        .st-key-login_right label {{
            font-weight: 500 !important;
            color: #374151 !important;
            font-size: 14px !important;
        }}
        
        /* Bouton submit ROUGE avec !important */
        .st-key-login_right div[data-testid="stFormSubmitButton"] button,
        .st-key-login_right button[kind="primary"] {{
            background: #ED1C24 !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 16px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            width: 100%;
            transition: background 0.2s ease, transform 0.1s ease;
            margin-top: 8px;
        }}
        
        .st-key-login_right div[data-testid="stFormSubmitButton"] button:hover,
        .st-key-login_right button[kind="primary"]:hover {{
            background: #B30006 !important;
            transform: translateY(-1px);
        }}
        
        .st-key-login_right div[data-testid="stFormSubmitButton"] button:active {{
            transform: translateY(0);
        }}
        
        /* Liens sous le formulaire */
        .form-links {{
            margin-top: 24px;
            text-align: center;
            display: flex;
            justify-content: space-between;
            gap: 12px;
        }}
        
        .form-links button {{
            color: #ED1C24 !important;
            background: transparent !important;
            border: none !important;
            text-decoration: none;
            font-size: 14px !important;
            padding: 8px 4px !important;
            font-weight: 500 !important;
            transition: opacity 0.2s ease;
        }}
        
        .form-links button:hover {{
            opacity: 0.8;
            text-decoration: underline;
        }}
        
        /* Bouton retour */
        .back-button {{
            margin-top: 20px;
        }}
        
        .back-button button {{
            color: #6B7280 !important;
            background: transparent !important;
            border: none !important;
            font-size: 14px !important;
            padding: 8px 4px !important;
        }}
        
        /* Selectbox département */
        .st-key-login_right div[data-baseweb="select"] {{
            background: #F3F4F7 !important;
            border-radius: 12px !important;
            border: 1px solid #E5E7EB !important;
        }}
        
        /* Responsive - Mobile */
        @media (max-width: 900px) {{
            .st-key-login_card {{
                flex-direction: column;
            }}
            
            .st-key-login_left {{
                min-height: 40vh;
                padding: 50px 30px;
            }}
            
            .login-left-content .wordmark {{
                width: 200px;
                margin-bottom: 30px;
            }}
            
            .login-left-content .brand-title {{
                font-size: 32px;
            }}
            
            .login-left-content .brand-subtitle {{
                font-size: 16px;
            }}
            
            /* Atténuer les bulles sur mobile */
            .st-key-login_left::before {{
                opacity: 0.5;
            }}
            
            .st-key-login_left::after {{
                opacity: 0.5;
            }}
            
            .emblem-bubble {{
                width: 120px;
                height: 120px;
                bottom: 30px;
                right: 30px;
            }}
            
            .emblem-bubble img {{
                width: 60px;
            }}
            
            .st-key-login_right {{
                padding: 50px 30px;
                min-height: 60vh;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
