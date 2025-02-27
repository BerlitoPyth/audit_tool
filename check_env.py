import os
import sys

def check_environment():
    """Vérifie que l'environnement est correctement configuré"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "backend", "data")
    required_dirs = [
        data_dir,
        os.path.join(data_dir, "files"),
        os.path.join(data_dir, "jobs"),
        os.path.join(data_dir, "results"),
    ]
    
    print("Vérification de l'environnement...")
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"✓ Dossier créé : {dir_path}")
        else:
            print(f"✓ Dossier existant : {dir_path}")
            
    print("\nVérification des permissions...")
    for dir_path in required_dirs:
        try:
            test_file = os.path.join(dir_path, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print(f"✓ Permissions OK pour : {dir_path}")
        except Exception as e:
            print(f"⨯ Erreur de permission pour {dir_path}: {str(e)}")
            
    print("\nEnvironnement vérifié!")

if __name__ == "__main__":
    check_environment()
