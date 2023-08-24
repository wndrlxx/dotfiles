" Get the defaults that most users want.
" source $VIMRUNTIME/defaults.vim
call plug#begin("~/.vim/plugged")
Plug 'itchyny/lightline.vim'
Plug 'preservim/nerdtree'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-endwise'
Plug 'tpope/vim-obsession'
Plug 'airblade/vim-gitgutter'
Plug 'scrooloose/nerdcommenter'
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'
Plug 'junegunn/vim-peekaboo'
Plug 'prettier/vim-prettier'
Plug 'chrisbra/Colorizer'
Plug 'vim-test/vim-test'
Plug 'tpope/vim-dispatch'
Plug 'mattn/vim-lsp-settings'
Plug 'prabirshrestha/vim-lsp'
Plug 'voldikss/vim-floaterm'
"Plug 'prabirshrestha/asyncomplete.vim'
"Plug 'prabirshrestha/asyncomplete-lsp.vim'
Plug 'dense-analysis/ale'
Plug 'maximbaz/lightline-ale'
Plug 'rainerborene/vim-reek'
Plug 'vim-ruby/vim-ruby'
Plug 'catppuccin/vim', { 'as': 'catppuccin' }
call plug#end()

" Put these in an autocmd group, so that we can delete them easily.
augroup vimrcEx
  au!
  autocmd FileType text setlocal textwidth=80
augroup END

filetype on
filetype plugin indent on    " required
syntax on

"colorscheme catppuccin_latte
"colorscheme catppuccin_frappe
"colorscheme catppuccin_macchiato
colorscheme catppuccin_mocha

" Show hybrid line numbers
set nocompatible              " be iMproved, required
set wildmode=longest,list   " get bash-like tab completions
set ttyfast                 " Speed up scrolling in Vim
" set spell                 " enable spell check (may need to download language package)
" set noswapfile            " disable creating swap file
" set backupdir=~/.cache/vim " Directory to store backup files.
set laststatus=2
set rtp+=/opt/homebrew/opt/fzf
set termguicolors     " enable true colors support
set number
set relativenumber
set hidden
set cursorline	      " highlight current line
set expandtab         " spaces not tabs
set tabstop=2
set autoindent
set copyindent
set shiftwidth=2
set smartindent
set smarttab
set softtabstop=2
set autoread                    " Automatically reread changed files without asking me anything
set incsearch                   " Shows the match while typing
set hlsearch                    " Highlight found searches
set ignorecase                  " Search case insensitive...
set smartcase                   " ... but not when search pattern contains upper case characters

" ale
let g:ruby_indent_assignment_style = 'variable'
let g:ruby_indent_hanging_elements = 0
let g:ale_linters = {
\   'ruby': ['rubocop'], 
\   'javascript': ['eslint'],
\}
let g:ale_fixers = {
\   '*': ['remove_trailing_lines', 'trim_whitespace'],
\   'ruby': ['rubocop'], 
\   'javascript': ['eslint'],
\}
let g:ale_virtualtext_cursor = 'disabled'
highlight clear ALEWarning
highlight clear ALEError
let g:ale_sign_warning = "\uf071"
let g:ale_sign_error = "\uf05e"
let g:lightline = {'colorscheme': 'catppuccin_mocha'}
let g:lightline.component_expand = {
      \  'linter_checking': 'lightline#ale#checking',
      \  'linter_infos': 'lightline#ale#infos',
      \  'linter_warnings': 'lightline#ale#warnings',
      \  'linter_errors': 'lightline#ale#errors',
      \  'linter_ok': 'lightline#ale#ok',
      \ }
let g:lightline.component_type = {
      \     'linter_checking': 'right',
      \     'linter_infos': 'right',
      \     'linter_warnings': 'warning',
      \     'linter_errors': 'error',
      \     'linter_ok': 'right',
      \ }
let g:lightline.active = { 'right': [[ 'linter_checking', 'linter_errors', 'linter_warnings', 'linter_infos', 'linter_ok' ]] }
let g:lightline.active = {
            \ 'right': [ [ 'linter_checking', 'linter_errors', 'linter_warnings', 'linter_infos', 'linter_ok' ],
            \            [ 'lineinfo' ],
	    \            [ 'percent' ],
	    \            [ 'fileformat', 'fileencoding', 'filetype'] ] }
let g:lightline#ale#indicator_checking = "\uf110"
let g:lightline#ale#indicator_infos = "\uf129"
let g:lightline#ale#indicator_warnings = "\uf071"
let g:lightline#ale#indicator_errors = "\uf05e"
let g:lightline#ale#indicator_ok = "\uf00c"
map <silent> <C-k> <Plug>(ale_previous_wrap)
map <silent> <C-j> <Plug>(ale_next_wrap)
nnoremap <C-X> :ALEFix<CR>

" NERDTree
let mapleader=";"
map <Leader>n :NERDTreeToggle<CR>
map <Tab>   <C-W>w

" vim-floaterm
noremap  <leader>lg :FloatermNew lazygit<CR>
let g:floaterm_width = 1.0
let g:floaterm_height = 1.0

" fzf search
nnoremap <leader>f :<C-u>FZF<CR>
nnoremap <leader>r :Rg<CR>

" Splits remap
" conflicts with <Plug>(ale_next_wrap)
" nnoremap <C-J> <C-W><C-J>
" conflicts with <Plug>(ale_previous_wrap)
" nnoremap <C-K> <C-W><C-K>
nnoremap <C-L> <C-W><C-L>
nnoremap <C-H> <C-W><C-H>
set splitbelow
set splitright

" Search and Replace
nmap <Leader>s :%s//gc<Left><Left><Left>

" copy/paste remap
noremap <C-c> :w !pbcopy<CR><CR> 
noremap <C-v> :r !pbpaste<CR><CR>

" folding
set foldmethod=indent
set foldnestmax=10
set nofoldenable
set foldnestmax=2

" vim-test
nmap <silent> <leader>t :TestNearest<CR>
nmap <silent> <leader>T :TestFile<CR>
nmap <silent> <leader>a :TestSuite<CR>
nmap <silent> <leader>l :TestLast<CR>
nmap <silent> <leader>g :TestVisit<CR>
let g:test#neovim#start_normal = 1
let test#ruby#bundle_exec = 0
let test#strategy = "neovim"
let test#ruby#rspec#options = '--format documentation --order random'
let test#neovim#term_position = "vert"

" vim-reek
nmap <leader>e :RunReek<CR>
let g:reek_on_loading = 0

" asyncomplete
inoremap <expr> <Tab>   pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"
inoremap <expr> <cr>    pumvisible() ? asyncomplete#close_popup() : "\<cr>"

" buffer
nnoremap <leader>j :bp<CR>
nnoremap <leader>k :bn<CR>

" save & exit
nmap <leader>w :w<CR>
nmap <leader>q :q<CR>
