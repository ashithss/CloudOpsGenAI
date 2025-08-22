#!/usr/bin/env python3
"""
AI-Powered DevOps Automation Tool
Analyzes repositories and generates Docker, K8s, and CI/CD configurations
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import git
import yaml

# Load environment variables
load_dotenv()

class DevOpsAITool:
    def __init__(self):
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('OLLAMA_MODEL', 'codellama:13b-instruct')
        self.output_dir = Path(os.getenv('OUTPUT_DIR', './generated_configs'))
        self.output_dir.mkdir(exist_ok=True)
    
    def clone_repository(self, repo_url, branch=None):
        """Clone a remote git repository to a temp folder and return the path"""
        from tempfile import TemporaryDirectory
        import git
        temp_dir = TemporaryDirectory()
        try:
            print(f"🔄 Cloning repository: {repo_url} (branch: {branch if branch else 'default'})")
            if branch:
                git.Repo.clone_from(repo_url, temp_dir.name, branch=branch)
            else:
                git.Repo.clone_from(repo_url, temp_dir.name)
            print(f"✅ Repository cloned to {temp_dir.name}")
            return temp_dir
        except Exception as e:
            print(f"❌ Error cloning repository: {e}")
            temp_dir.cleanup()
            return None
        
    def check_ollama_connection(self):
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                if self.model_name in model_names:
                    print(f"✅ Connected to Ollama. Model {self.model_name} is ready.")
                    return True
                else:
                    print(f"❌ Model {self.model_name} not found. Available models: {model_names}")
                    return False
            else:
                print(f"❌ Cannot connect to Ollama at {self.ollama_host}")
                return False
        except Exception as e:
            print(f"❌ Error connecting to Ollama: {e}")
            return False

    def analyze_repository(self, repo_path):
        """Analyze repository structure and detect tech stack"""
        repo_path = Path(repo_path)
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path {repo_path} does not exist")
        
        analysis = {
            'languages': [],
            'frameworks': [],
            'package_managers': {},
            'entry_points': [],
            'dependencies': {},
            'structure': {},
            'is_web_app': False,
            'default_port': 3000
        }
        
        # Detect package managers and dependencies
        package_files = {
            'package.json': 'node',
            'requirements.txt': 'python',
            'Pipfile': 'python',
            'setup.py': 'python',
            'pom.xml': 'java',
            'build.gradle': 'java',
            'Cargo.toml': 'rust',
            'go.mod': 'go',
            'composer.json': 'php'
        }
        
        for file_name, lang in package_files.items():
            file_path = repo_path / file_name
            if file_path.exists():
                analysis['languages'].append(lang)
                analysis['package_managers'][file_name] = True
                
                # Parse specific files for more details
                if file_name == 'package.json' and file_path.exists():
                    try:
                        with open(file_path) as f:
                            pkg_json = json.load(f)
                            analysis['dependencies']['node'] = {
                                'name': pkg_json.get('name', 'unknown'),
                                'main': pkg_json.get('main', 'index.js'),
                                'scripts': pkg_json.get('scripts', {}),
                                'dependencies': list(pkg_json.get('dependencies', {}).keys())
                            }
                            
                            # Check if it's a web app based on dependencies
                            deps = pkg_json.get('dependencies', {})
                            web_frameworks = ['express', 'react', 'vue', 'angular', 'next', 'nuxt', 'fastify', 'koa']
                            if any(fw in deps for fw in web_frameworks):
                                analysis['is_web_app'] = True
                                analysis['default_port'] = 3000
                                
                    except Exception as e:
                        print(f"Warning: Could not parse package.json: {e}")
                        
                elif file_name == 'requirements.txt' and file_path.exists():
                    try:
                        with open(file_path) as f:
                            reqs = [line.strip().split('==')[0] for line in f if line.strip() and not line.startswith('#')]
                            analysis['dependencies']['python'] = reqs
                            
                            # Check if it's a web app based on dependencies
                            web_frameworks = ['flask', 'django', 'fastapi', 'tornado', 'pyramid', 'bottle']
                            if any(fw.lower() in [r.lower() for r in reqs] for fw in web_frameworks):
                                analysis['is_web_app'] = True
                                analysis['default_port'] = 8000 if 'fastapi' in [r.lower() for r in reqs] else 5000
                                
                    except Exception as e:
                        print(f"Warning: Could not parse requirements.txt: {e}")
        
        # Detect common files and structure
        common_files = [
            'Dockerfile', 'docker-compose.yml', '.dockerignore',
            'README.md', 'LICENSE', '.gitignore',
            'main.py', 'app.py', 'server.js', 'index.js'
        ]
        
        for file_name in common_files:
            if (repo_path / file_name).exists():
                analysis['structure'][file_name] = True
                if file_name in ['main.py', 'app.py', 'server.js', 'index.js']:
                    analysis['entry_points'].append(file_name)
        
        return analysis

    def generate_dockerfile(self, analysis):
        """Generate Dockerfile based on repository analysis"""
        
        prompt = self._create_dockerfile_prompt(analysis)
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                dockerfile_content = result.get('response', '').strip()
                return self._clean_dockerfile_response(dockerfile_content)
            else:
                raise Exception(f"API request failed: {response.status_code}")
                
        except Exception as e:
            print(f"Error generating Dockerfile: {e}")
            return None

    def _create_dockerfile_prompt(self, analysis):
        """Create a structured prompt for Dockerfile generation"""
        
        primary_lang = analysis['languages'][0] if analysis['languages'] else 'unknown'
        dependencies = analysis.get('dependencies', {})
        entry_points = analysis.get('entry_points', [])
        
        prompt = f"""You are an expert DevOps engineer. Create an optimized, production-ready Dockerfile.

Repository Analysis:
- Primary Language: {primary_lang}
- Dependencies: {json.dumps(dependencies, indent=2)}
- Entry Points: {entry_points}
- Package Managers: {list(analysis['package_managers'].keys())}
- Is Web App: {analysis.get('is_web_app', False)}
- Default Port: {analysis.get('default_port', 3000)}

Requirements:
1. Use multi-stage build for optimization
2. Follow security best practices (non-root user, minimal base image)
3. Optimize for image size
4. Include proper COPY instructions for dependencies
5. Set appropriate WORKDIR
6. Use proper EXPOSE directive if it's a web application
7. Include health check if appropriate

Generate ONLY the Dockerfile content, no explanations or additional text:"""
        
        return prompt
    
    def generate_k8s_manifests(self, analysis):
        """Generate Kubernetes manifests based on repository analysis"""
        
        prompt = self._create_k8s_prompt(analysis)
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                manifests_content = result.get('response', '').strip()
                return self._clean_k8s_response(manifests_content)
            else:
                raise Exception(f"API request failed: {response.status_code}")
                
        except Exception as e:
            print(f"Error generating K8s manifests: {e}")
            return None

    def _create_k8s_prompt(self, analysis):
        """Create a structured prompt for Kubernetes manifests generation"""
        
        app_name = "myapp"
        if analysis.get('dependencies', {}).get('node', {}).get('name'):
            app_name = analysis['dependencies']['node']['name'].replace('_', '-').replace(' ', '-').lower()
        
        primary_lang = analysis['languages'][0] if analysis['languages'] else 'unknown'
        is_web_app = analysis.get('is_web_app', False)
        default_port = analysis.get('default_port', 3000)
        
        prompt = f"""You are an expert Kubernetes engineer. Generate production-ready Kubernetes manifests.

Repository Analysis:
- App Name: {app_name}
- Primary Language: {primary_lang}
- Is Web Application: {is_web_app}
- Default Port: {default_port}
- Entry Points: {analysis.get('entry_points', [])}
- Dependencies: {json.dumps(analysis.get('dependencies', {}), indent=2)}

Requirements:
1. Generate Deployment, Service, and ConfigMap manifests
2. Use image '{app_name}:latest'
3. Set replicas to 3 for high availability
4. Include resource limits and requests
5. Add liveness and readiness probes if it's a web app
6. Expose port {default_port} if it's a web service
7. Use proper labels and selectors
8. Include appropriate environment variables
9. Follow Kubernetes best practices

Generate ONLY the YAML manifests separated by '---', no explanations:"""
        
        return prompt

    def _clean_dockerfile_response(self, response):
        """Clean up the Dockerfile response from the model"""
        # Remove any markdown code blocks
        response = response.replace('```dockerfile', '').replace('```', '').replace('```docker', '')
        
        # Split into lines and clean
        lines = []
        for line in response.split('\n'):
            line = line.strip()
            if line and not line.startswith('Here') and not line.startswith('This'):
                lines.append(line)
        
        return '\n'.join(lines)

    def _clean_k8s_response(self, response):
        """Clean up the K8s manifests response from the model"""
        # Remove any markdown code blocks
        response = response.replace('```yaml', '').replace('```yml', '').replace('```', '')
        
        # Remove explanatory text that might be at the beginning
        lines = response.split('\n')
        cleaned_lines = []
        yaml_started = False
        
        for line in lines:
            if not yaml_started:
                # Look for YAML content starting
                if line.strip().startswith('apiVersion:') or line.strip().startswith('---'):
                    yaml_started = True
                    cleaned_lines.append(line)
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def save_generated_config(self, content, filename):
        """Save generated configuration to output directory"""
        output_path = self.output_dir / filename
        try:
            with open(output_path, 'w') as f:
                f.write(content)
            print(f"✅ Generated {filename} saved to {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Error saving {filename}: {e}")
            return None

def main():
    """Main application entry point"""
    print("🚀 AI-Powered DevOps Automation Tool")
    print("=" * 50)
    
    tool = DevOpsAITool()
    
    if not tool.check_ollama_connection():
        print("Please start Ollama and ensure the model is downloaded.")
        print("Run: ollama serve")
        print(f"Run: ollama pull {tool.model_name}")
        sys.exit(1)
    
    # Accept repo path and branch from command line or prompt
    if len(sys.argv) > 2:
        repo_path = sys.argv[1]
        branch = sys.argv[2]
    else:
        repo_path = input("Enter repository path or git URL (or press Enter for current directory): ").strip()
        if not repo_path:
            repo_path = "."
        branch = input("Enter branch name (or press Enter for default): ").strip()
        if not branch:
            branch = None

    # Check if repo_path looks like a git URL
    if repo_path.startswith("http://") or repo_path.startswith("https://") or repo_path.endswith(".git"):
        temp_dir = tool.clone_repository(repo_path, branch)
        if not temp_dir:
            sys.exit(1)
        repo_path = temp_dir.name

    try:
        print(f"\n📁 Analyzing repository: {repo_path}")
        analysis = tool.analyze_repository(repo_path)
        print(f"✅ Analysis complete:")
        print(f"   Languages: {', '.join(analysis['languages'])}")
        print(f"   Package Managers: {', '.join(analysis['package_managers'].keys())}")
        print(f"   Entry Points: {', '.join(analysis['entry_points'])}")
        print(f"   Web Application: {analysis.get('is_web_app', False)}")
        print(f"   Default Port: {analysis.get('default_port', 'N/A')}")

        # Generate Dockerfile
        print(f"\n🐳 Generating Dockerfile...")
        dockerfile_content = tool.generate_dockerfile(analysis)
        if dockerfile_content:
            dockerfile_path = tool.save_generated_config(dockerfile_content, "Dockerfile")
            if dockerfile_path:
                print(f"\n📄 Generated Dockerfile Preview:")
                print("-" * 40)
                print(dockerfile_content[:500] + "..." if len(dockerfile_content) > 500 else dockerfile_content)
                print("-" * 40)
        else:
            print("❌ Failed to generate Dockerfile")

        # # Generate Kubernetes manifests
        # print(f"\n☸️  Generating Kubernetes manifests...")
        # k8s_content = tool.generate_k8s_manifests(analysis)
        # if k8s_content:
        #     k8s_path = tool.save_generated_config(k8s_content, "k8s-manifests.yaml")
        #     if k8s_path:
        #         print(f"\n📄 Generated K8s Manifests Preview:")
        #         print("-" * 40)
        #         print(k8s_content[:500] + "..." if len(k8s_content) > 500 else k8s_content)
        #         print("-" * 40)
                
        #         # Split and save individual manifest files
        #         manifests = k8s_content.split('---')
        #         for i, manifest in enumerate(manifests):
        #             if manifest.strip():
        #                 # Try to determine manifest type from content
        #                 manifest_type = "unknown"
        #                 if "kind: Deployment" in manifest:
        #                     manifest_type = "deployment"
        #                 elif "kind: Service" in manifest:
        #                     manifest_type = "service"
        #                 elif "kind: ConfigMap" in manifest:
        #                     manifest_type = "configmap"
        #                 elif "kind: Ingress" in manifest:
        #                     manifest_type = "ingress"
                        
        #                 individual_path = tool.save_generated_config(
        #                     manifest.strip(), 
        #                     f"k8s-{manifest_type}-{i}.yaml"
        #                 )
        # else:
        #     print("❌ Failed to generate Kubernetes manifests")

        print(f"\n🎉 Generation complete! Check the '{tool.output_dir}' directory for all generated files.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()