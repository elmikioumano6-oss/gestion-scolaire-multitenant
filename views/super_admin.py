with tab2:
            st.markdown("### Enregistrer un Nouvel Établissement et son Administrateur")
            with st.form("form_create_school"):
                st.markdown("#### 1. Informations de l'établissement")
                code_ecole = st.text_input("Code unique de l'établissement (ex: RAHMAT, CHALLENGE)")
                nom_ecole = st.text_input("Nom de l'établissement")
                devise_ecole = st.text_input("Devise", value="Discipline - Qualité - Réussite")
                adresse_ecole = st.text_input("Adresse / Quartier, Ville", value="Niamey, Niger")
                contacts_ecole = st.text_input("Numéros de téléphone (séparés par /)")
                
                # Modification ici : Période d'essai fixée par défaut à 14 jours pour s'aligner sur la page en ligne
                periode_essai_jours = st.number_input("Période d'essai (en jours)", min_value=1, max_value=365, value=14)

                st.markdown("#### 2. Compte Administrateur / Censeur initial")
                admin_username = st.text_input("Identifiant de connexion (ex: admin_rahmat)")
                admin_password = st.text_input("Mot de passe provisoire", type="password")

                submitted_school = st.form_submit_button("Créer l'établissement et générer le compte")
                
                if submitted_school:
                    if not nom_ecole.strip() or not code_ecole.strip():
                        st.error("⚠️ Le nom et le code unique de l'établissement sont obligatoires.")
                    elif not admin_username.strip() or not admin_password.strip():
                        st.error("⚠️ L'identifiant et le mot de passe administrateur sont obligatoires.")
                    elif len(admin_password) < 6:
                        st.error("⚠️ Le mot de passe provisoire doit contenir au moins 6 caractères.")
                    else:
                        code_nettoye = code_ecole.strip().upper()
                        code_existant = db.query(School).filter(School.code == code_nettoye).first()
                        
                        if code_existant:
                            st.error(f"⚠️ Un établissement avec le code '{code_nettoye}' existe déjà.")
                        else:
                            user_existant = db.query(User).filter(User.username == admin_username.strip()).first()
                            
                            if user_existant:
                                st.error(f"⚠️ L'identifiant '{admin_username.strip()}' est déjà utilisé.")
                            else:
                                # Calcul de la date d'expiration basée sur les jours d'essai saisis (14 jours par défaut)
                                date_expiration_val = datetime.now() + timedelta(days=periode_essai_jours)
                                
                                nouvelle_ecole = School(
                                    code=code_nettoye,
                                    nom=nom_ecole.strip(),
                                    devise=devise_ecole.strip(),
                                    adresse=adresse_ecole.strip(),
                                    contacts=contacts_ecole.strip(),
                                    actif=True,
                                    date_expiration=date_expiration_val,
                                    is_trial=True, # Marqué comme essai par défaut
                                    trial_expires_at=date_expiration_val,
                                )
                                db.add(nouvelle_ecole)
                                db.commit()
                                db.refresh(nouvelle_ecole)

                                hashed_pwd = bcrypt.hashpw(
                                    admin_password.encode("utf-8"), bcrypt.gensalt()
                                ).decode("utf-8")
                                nouvel_admin = User(
                                    school_id=nouvelle_ecole.id,
                                    username=admin_username.strip(),
                                    password=hashed_pwd,
                                    role="admin",
                                    changer_mdp_requis=True,
                                )
                                db.add(nouvel_admin)

                                log_action_erp(
                                    module="Gestion des Tenants",
                                    action=f"Création du nouvel établissement '{nom_ecole.strip()}' (Code: {code_nettoye})",
                                    statut="Succès",
                                    valeur_avant="Inexistant",
                                    valeur_apres=f"Créé avec admin '{admin_username.strip()}' (Essai 14j)",
                                )
                                db.commit()

                                st.session_state["last_created_credentials"] = {
                                    "school_name": nom_ecole.strip(),
                                    "username": admin_username.strip(),
                                    "password": admin_password.strip(),
                                    "contacts": contacts_ecole.strip(),
                                }

                                st.success(
                                    f"✅ L'établissement **{nom_ecole}** et son compte "
                                    "administrateur ont été créés avec succès (Essai de 14 jours) !"
                                )
                                st.rerun()